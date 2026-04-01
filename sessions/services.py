import logging
import random
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from billing.services import BillingService, TariffService
from chargers.models import ChargePoint, Connector
from rfid.services import RFIDService
from sessions.models import ChargingSession, MeterValue

logger = logging.getLogger('ocpp')


class SessionService:

    @staticmethod
    def _generate_transaction_id():
        """Generate a unique transaction ID (positive integer as required by OCPP)."""
        for _ in range(10):
            tid = random.randint(100000, 99999999)
            if not ChargingSession.objects.filter(transaction_id=tid).exists():
                return tid
        raise RuntimeError('Could not generate unique transaction ID')

    @staticmethod
    def start_session(*, charge_point_id, connector_id, id_tag, meter_start, timestamp):
        """
        Called by StartTransaction OCPP handler.
        Returns (transaction_id, id_tag_info_dict).
        """
        # Authorize the tag
        auth_result = RFIDService.authorize_id_tag(id_tag)
        if auth_result['status'] != 'Accepted':
            tid = SessionService._generate_transaction_id()
            # Create invalid session for audit
            ChargingSession.objects.create(
                transaction_id=tid,
                charge_point_id_str=charge_point_id,
                id_tag=id_tag,
                meter_start_wh=meter_start,
                status=ChargingSession.Status.INVALID,
                started_at=_parse_ts(timestamp),
            )
            return tid, {'status': auth_result['status']}

        # Prevent concurrent sessions for same RFID card
        existing_active = ChargingSession.objects.filter(
            id_tag=id_tag,
            status=ChargingSession.Status.ACTIVE,
        ).first()
        if existing_active:
            logger.warning(
                'StartTransaction rejected: idTag %s already has active session txn=%s',
                id_tag, existing_active.transaction_id,
            )
            tid = SessionService._generate_transaction_id()
            ChargingSession.objects.create(
                transaction_id=tid,
                charge_point_id_str=charge_point_id,
                id_tag=id_tag,
                meter_start_wh=meter_start,
                status=ChargingSession.Status.INVALID,
                stop_reason='ConcurrentTx',
                started_at=_parse_ts(timestamp),
            )
            return tid, {'status': 'ConcurrentTx'}

        # Prevent two sessions on the same connector at the same time
        if connector_id:
            existing_on_connector = ChargingSession.objects.filter(
                charge_point_id_str=charge_point_id,
                connector__connector_id=connector_id,
                status=ChargingSession.Status.ACTIVE,
            ).first()
            if existing_on_connector:
                logger.warning(
                    'StartTransaction rejected: connector %s on %s already has active session txn=%s',
                    connector_id, charge_point_id, existing_on_connector.transaction_id,
                )
                tid = SessionService._generate_transaction_id()
                ChargingSession.objects.create(
                    transaction_id=tid,
                    charge_point_id_str=charge_point_id,
                    id_tag=id_tag,
                    meter_start_wh=meter_start,
                    status=ChargingSession.Status.INVALID,
                    stop_reason='ConcurrentTx',
                    started_at=_parse_ts(timestamp),
                )
                return tid, {'status': 'ConcurrentTx'}

        # Block if no active tariff configured (would result in free charging)
        tariff_price = TariffService.get_active_price_per_kwh()
        if tariff_price <= 0:
            logger.error(
                'StartTransaction rejected: no active tariff configured (price=%.4f)',
                tariff_price,
            )
            tid = SessionService._generate_transaction_id()
            ChargingSession.objects.create(
                transaction_id=tid,
                charge_point_id_str=charge_point_id,
                id_tag=id_tag,
                meter_start_wh=meter_start,
                status=ChargingSession.Status.INVALID,
                stop_reason='NoTariff',
                started_at=_parse_ts(timestamp),
            )
            return tid, {'status': 'Blocked'}

        # Get customer from RFID
        customer = RFIDService.get_customer_for_id_tag(id_tag)

        # Check wallet balance
        if customer:
            can_start, reason = BillingService.check_can_start(customer.wallet.pk)
            if not can_start:
                logger.warning(
                    'StartTransaction rejected for %s: %s', id_tag, reason,
                )
                tid = SessionService._generate_transaction_id()
                ChargingSession.objects.create(
                    transaction_id=tid,
                    charge_point_id_str=charge_point_id,
                    id_tag=id_tag,
                    customer=customer,
                    meter_start_wh=meter_start,
                    status=ChargingSession.Status.INVALID,
                    stop_reason='InsufficientBalance',
                    started_at=_parse_ts(timestamp),
                )
                return tid, {'status': 'Blocked'}

        # Resolve charge point and connector
        try:
            cp = ChargePoint.objects.get(charge_point_id=charge_point_id)
        except ChargePoint.DoesNotExist:
            cp = None

        connector_obj = None
        if cp and connector_id:
            connector_obj = Connector.objects.filter(
                charge_point=cp, connector_id=connector_id,
            ).first()

        rfid_card = None
        try:
            from rfid.models import RFIDCard
            rfid_card = RFIDCard.objects.get(id_tag=id_tag)
        except Exception:
            pass

        # tariff_price already fetched above (zero-tariff check)

        # Generate transaction ID and create session
        tid = SessionService._generate_transaction_id()
        started = _parse_ts(timestamp) or timezone.now()

        session = ChargingSession.objects.create(
            transaction_id=tid,
            charge_point=cp,
            connector=connector_obj,
            rfid_card=rfid_card,
            customer=customer,
            id_tag=id_tag,
            charge_point_id_str=charge_point_id,
            status=ChargingSession.Status.ACTIVE,
            meter_start_wh=meter_start,
            tariff_per_kwh=tariff_price,
            started_at=started,
        )

        logger.info(
            'Session started: txn=%s cp=%s connector=%s tag=%s tariff=%.4f',
            tid, charge_point_id, connector_id, id_tag, tariff_price,
        )

        id_tag_info = {'status': 'Accepted'}
        if auth_result.get('expiry_date'):
            id_tag_info['expiryDate'] = auth_result['expiry_date']

        return tid, id_tag_info

    @staticmethod
    def stop_session(*, transaction_id, meter_stop, timestamp,
                     id_tag='', reason='', transaction_data=None):
        """
        Called by StopTransaction OCPP handler.
        Finalizes session, calculates cost, deducts from wallet.
        """
        stopped = _parse_ts(timestamp) or timezone.now()

        with transaction.atomic():
            # Lock the session row to prevent race with concurrent MeterValues
            try:
                session = ChargingSession.objects.select_for_update(
                    of=('self',)
                ).select_related(
                    'customer', 'customer__wallet',
                ).get(transaction_id=transaction_id)
            except ChargingSession.DoesNotExist:
                logger.warning('StopTransaction for unknown txn=%s', transaction_id)
                return

            if session.status != ChargingSession.Status.ACTIVE:
                logger.warning('StopTransaction for non-active session txn=%s (status=%s)',
                               transaction_id, session.status)
                return

            # Calculate energy
            energy_wh = max(0, meter_stop - session.meter_start_wh)
            energy_kwh = Decimal(energy_wh) / Decimal('1000')

            # Calculate duration
            duration = None
            if session.started_at:
                delta = stopped - session.started_at
                duration = int(delta.total_seconds())

            session.meter_stop_wh = meter_stop
            session.energy_delivered_wh = energy_wh
            session.energy_delivered_kwh = energy_kwh.quantize(Decimal('0.001'))
            session.status = ChargingSession.Status.COMPLETED
            session.stop_reason = reason
            session.stopped_at = stopped
            session.duration_seconds = duration
            session.save(update_fields=[
                'meter_stop_wh', 'energy_delivered_wh', 'energy_delivered_kwh',
                'status', 'stop_reason', 'stopped_at', 'duration_seconds', 'updated_at',
            ])

            # Finalize billing
            BillingService.finalize_session_billing(session)

        # Store transaction data as meter values if provided
        if transaction_data:
            SessionService._store_transaction_data(session, transaction_data)

        logger.info(
            'Session stopped: txn=%s energy=%.3f kWh cost=%.2f ILS reason=%s',
            transaction_id, energy_kwh, session.total_cost, reason,
        )

    @staticmethod
    def update_meter_values(*, connector_id_ocpp, charge_point_id,
                            transaction_id, meter_values_payload):
        """
        Called by MeterValues OCPP handler.
        Stores meter readings, updates session energy, triggers real-time billing.
        """
        # Resolve connector
        connector_obj = None
        try:
            cp = ChargePoint.objects.get(charge_point_id=charge_point_id)
            if connector_id_ocpp:
                connector_obj = Connector.objects.filter(
                    charge_point=cp, connector_id=connector_id_ocpp,
                ).first()
        except ChargePoint.DoesNotExist:
            pass

        latest_energy_wh = None
        auto_stop_needed = False

        with transaction.atomic():
            session = None
            if transaction_id:
                try:
                    session = ChargingSession.objects.select_for_update(
                        of=('self',)
                    ).select_related(
                        'customer', 'customer__wallet',
                    ).get(
                        transaction_id=transaction_id,
                        status=ChargingSession.Status.ACTIVE,
                    )
                except ChargingSession.DoesNotExist:
                    pass

            for mv_group in meter_values_payload:
                ts = _parse_ts(mv_group.get('timestamp')) or timezone.now()
                sampled_values = mv_group.get('sampledValue', [])

                for sv in sampled_values:
                    measurand = sv.get('measurand', 'Energy.Active.Import.Register')
                    value = sv.get('value', '0')
                    unit = sv.get('unit', 'Wh')
                    phase = sv.get('phase', '')
                    context = sv.get('context', 'Sample.Periodic')
                    location = sv.get('location', 'Outlet')
                    fmt = sv.get('format', 'Raw')

                    if session:
                        MeterValue.objects.create(
                            session=session,
                            connector=connector_obj,
                            timestamp=ts,
                            measurand=measurand,
                            value=value,
                            unit=unit,
                            phase=phase,
                            context=context,
                            location=location,
                            format=fmt,
                        )

                    # Track energy for session update
                    if measurand == 'Energy.Active.Import.Register':
                        try:
                            val = Decimal(value)
                            if unit == 'kWh':
                                val = val * Decimal('1000')
                            latest_energy_wh = int(val)
                        except Exception:
                            pass

            # Update session with latest energy reading
            if session and latest_energy_wh is not None:
                # Meter rollover detection: if new reading < last known,
                # the charger likely rebooted. Keep the higher value.
                if latest_energy_wh < session.meter_start_wh and session.energy_delivered_wh > 0:
                    logger.warning(
                        'Meter rollover detected for session %s: new=%d < start=%d. '
                        'Keeping last known energy=%d Wh',
                        session.transaction_id, latest_energy_wh,
                        session.meter_start_wh, session.energy_delivered_wh,
                    )
                    # Don't update energy — keep the last valid calculation
                else:
                    energy_wh = max(0, latest_energy_wh - session.meter_start_wh)
                    energy_kwh = Decimal(energy_wh) / Decimal('1000')

                    session.energy_delivered_wh = energy_wh
                    session.energy_delivered_kwh = energy_kwh.quantize(Decimal('0.001'))
                    session.total_cost = BillingService.calculate_cost(energy_kwh, session.tariff_per_kwh)
                    session.save(update_fields=[
                        'energy_delivered_wh', 'energy_delivered_kwh', 'total_cost', 'updated_at',
                    ])

                    # Real-time billing deduction
                    BillingService.process_realtime_deduction(session)

                    # Check auto-stop (send outside atomic block)
                    if BillingService.should_auto_stop(session):
                        auto_stop_needed = True

        # Send auto-stop outside the atomic block to avoid holding locks
        if auto_stop_needed and session:
            logger.warning(
                'Auto-stop triggered for session %s (low balance)',
                session.transaction_id,
            )
            try:
                from ocpp_app.services import OCPPService
                OCPPService.send_remote_stop(
                    session.charge_point_id_str,
                    session.transaction_id,
                )
            except Exception:
                logger.exception('Failed to send auto-stop for session %s',
                                 session.transaction_id)

    @staticmethod
    def _store_transaction_data(session, transaction_data):
        """Store transactionData from StopTransaction as MeterValue records."""
        for mv_group in transaction_data:
            ts = _parse_ts(mv_group.get('timestamp')) or timezone.now()
            for sv in mv_group.get('sampledValue', []):
                MeterValue.objects.create(
                    session=session,
                    connector=session.connector,
                    timestamp=ts,
                    measurand=sv.get('measurand', 'Energy.Active.Import.Register'),
                    value=sv.get('value', '0'),
                    unit=sv.get('unit', 'Wh'),
                    phase=sv.get('phase', ''),
                    context=sv.get('context', 'Transaction.End'),
                    location=sv.get('location', 'Outlet'),
                    format=sv.get('format', 'Raw'),
                )

    @staticmethod
    def reactivate_on_reconnect(charge_point_id):
        """
        Called on BootNotification. Reactivate sessions that were marked as faulted
        by a recent server restart (within last 5 minutes) — the charger may still
        be actively charging.
        """
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=5)
        recently_faulted = ChargingSession.objects.filter(
            charge_point_id_str=charge_point_id,
            status=ChargingSession.Status.FAULTED,
            stop_reason='PowerLoss',
            stopped_at__gte=cutoff,
        )
        for session in recently_faulted:
            session.status = ChargingSession.Status.ACTIVE
            session.billing_status = ChargingSession.BillingStatus.PENDING
            session.stop_reason = ''
            session.stopped_at = None
            session.duration_seconds = None
            session.meter_stop_wh = 0
            session.save(update_fields=[
                'status', 'billing_status', 'stop_reason', 'stopped_at',
                'duration_seconds', 'meter_stop_wh', 'updated_at',
            ])
            logger.info(
                'Reactivated session txn=%s on charger reconnect (was faulted by server restart)',
                session.transaction_id,
            )

    @staticmethod
    def handle_charger_disconnect(charge_point_id):
        """
        Called when a charger disconnects unexpectedly.
        Finalizes any orphaned ACTIVE sessions with last known meter values.
        """
        orphaned = ChargingSession.objects.select_related(
            'customer', 'customer__wallet',
        ).filter(
            charge_point_id_str=charge_point_id,
            status=ChargingSession.Status.ACTIVE,
        )
        for session in orphaned:
            logger.warning(
                'Orphaned session detected on disconnect: txn=%s cp=%s',
                session.transaction_id, charge_point_id,
            )
            try:
                stopped = timezone.now()
                energy_wh = session.energy_delivered_wh  # Use last known value
                energy_kwh = Decimal(energy_wh) / Decimal('1000')

                duration = None
                if session.started_at:
                    duration = int((stopped - session.started_at).total_seconds())

                with transaction.atomic():
                    session.meter_stop_wh = session.meter_start_wh + energy_wh
                    session.energy_delivered_wh = energy_wh
                    session.energy_delivered_kwh = energy_kwh.quantize(Decimal('0.001'))
                    session.status = ChargingSession.Status.FAULTED
                    session.stop_reason = 'PowerLoss'
                    session.stopped_at = stopped
                    session.duration_seconds = duration
                    session.save(update_fields=[
                        'meter_stop_wh', 'energy_delivered_wh', 'energy_delivered_kwh',
                        'status', 'stop_reason', 'stopped_at', 'duration_seconds', 'updated_at',
                    ])

                    # Bill for energy already delivered
                    BillingService.finalize_session_billing(session)

                logger.info(
                    'Orphaned session finalized: txn=%s energy=%.3f kWh cost=%.2f',
                    session.transaction_id, energy_kwh, session.total_cost,
                )
            except Exception:
                logger.exception('Failed to finalize orphaned session txn=%s',
                                 session.transaction_id)

    @staticmethod
    def force_close_session(*, transaction_id, reason='AdminForceClose'):
        """
        Force-close a stuck/frozen session from the server side.
        Works even if the charger is offline. Finalizes billing with
        the last known energy reading.
        """
        stopped = timezone.now()

        with transaction.atomic():
            try:
                session = ChargingSession.objects.select_for_update(
                    of=('self',)
                ).select_related(
                    'customer', 'customer__wallet',
                ).get(transaction_id=transaction_id)
            except ChargingSession.DoesNotExist:
                logger.warning('Force-close: unknown txn=%s', transaction_id)
                return None

            if session.status != ChargingSession.Status.ACTIVE:
                logger.warning('Force-close: session txn=%s already %s',
                               transaction_id, session.status)
                return session

            energy_wh = session.energy_delivered_wh
            energy_kwh = Decimal(energy_wh) / Decimal('1000')

            duration = None
            if session.started_at:
                duration = int((stopped - session.started_at).total_seconds())

            session.meter_stop_wh = session.meter_start_wh + energy_wh
            session.energy_delivered_wh = energy_wh
            session.energy_delivered_kwh = energy_kwh.quantize(Decimal('0.001'))
            session.status = ChargingSession.Status.COMPLETED
            session.stop_reason = reason
            session.stopped_at = stopped
            session.duration_seconds = duration
            session.save(update_fields=[
                'meter_stop_wh', 'energy_delivered_wh', 'energy_delivered_kwh',
                'status', 'stop_reason', 'stopped_at', 'duration_seconds', 'updated_at',
            ])

            BillingService.finalize_session_billing(session)

        logger.info(
            'Session force-closed: txn=%s energy=%.3f kWh cost=%.2f ILS reason=%s',
            transaction_id, energy_kwh, session.total_cost, reason,
        )
        return session

    @staticmethod
    def get_active_sessions():
        return ChargingSession.objects.filter(
            status=ChargingSession.Status.ACTIVE,
        ).select_related('charge_point', 'connector', 'customer')

    @staticmethod
    def get_session_by_transaction_id(transaction_id):
        return ChargingSession.objects.select_related(
            'charge_point', 'connector', 'rfid_card', 'customer',
        ).get(transaction_id=transaction_id)


def _parse_ts(ts_string):
    """Parse an ISO 8601 timestamp string, return None on failure."""
    if not ts_string:
        return None
    try:
        dt = parse_datetime(ts_string)
        if dt and dt.tzinfo is None:
            from django.utils.timezone import make_aware
            dt = make_aware(dt)
        return dt
    except Exception:
        return None
