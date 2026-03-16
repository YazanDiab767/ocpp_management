"""
Management command to detect and fix problematic sessions.

Handles:
1. Orphaned ACTIVE sessions (charger offline for too long)
2. Failed billing retries (billing_status='failed')
3. Heartbeat timeout detection (mark chargers offline)

Run periodically via cron/scheduler:
    python manage.py cleanup_sessions
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billing.services import BillingService
from chargers.models import ChargePoint
from sessions.models import ChargingSession

logger = logging.getLogger('ocpp')


class Command(BaseCommand):
    help = 'Clean up orphaned sessions, retry failed billing, detect heartbeat timeouts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-timeout',
            type=int,
            default=30,
            help='Minutes after which an ACTIVE session on an OFFLINE charger is considered orphaned (default: 30)',
        )
        parser.add_argument(
            '--heartbeat-timeout',
            type=int,
            default=10,
            help='Minutes after which a charger with no heartbeat is marked OFFLINE (default: 10)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        session_timeout = options['session_timeout']
        heartbeat_timeout = options['heartbeat_timeout']
        dry_run = options['dry_run']
        now = timezone.now()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be made'))

        # 1. Heartbeat timeout: mark chargers as OFFLINE
        heartbeat_cutoff = now - timedelta(minutes=heartbeat_timeout)
        stale_chargers = ChargePoint.objects.filter(
            status=ChargePoint.Status.ONLINE,
            last_heartbeat__lt=heartbeat_cutoff,
        )
        for cp in stale_chargers:
            mins_ago = (now - cp.last_heartbeat).total_seconds() / 60
            self.stdout.write(
                f'  Heartbeat timeout: {cp.charge_point_id} '
                f'(last heartbeat {mins_ago:.0f} min ago)'
            )
            if not dry_run:
                cp.status = ChargePoint.Status.OFFLINE
                cp.save(update_fields=['status', 'updated_at'])
                logger.warning(
                    'Heartbeat timeout: %s marked OFFLINE (last heartbeat %s)',
                    cp.charge_point_id, cp.last_heartbeat,
                )

        self.stdout.write(f'Heartbeat timeouts: {stale_chargers.count()}')

        # 2. Orphaned ACTIVE sessions on OFFLINE chargers
        session_cutoff = now - timedelta(minutes=session_timeout)
        offline_charger_ids = list(
            ChargePoint.objects.filter(
                status__in=[ChargePoint.Status.OFFLINE, ChargePoint.Status.FAULTED],
            ).values_list('charge_point_id', flat=True)
        )

        orphaned = ChargingSession.objects.select_related(
            'customer', 'customer__wallet',
        ).filter(
            status=ChargingSession.Status.ACTIVE,
            charge_point_id_str__in=offline_charger_ids,
            updated_at__lt=session_cutoff,
        )

        orphan_count = 0
        for session in orphaned:
            orphan_count += 1
            self.stdout.write(
                f'  Orphaned session: txn={session.transaction_id} '
                f'cp={session.charge_point_id_str} '
                f'energy={session.energy_delivered_wh}Wh '
                f'last_update={session.updated_at}'
            )
            if not dry_run:
                try:
                    with transaction.atomic():
                        energy_wh = session.energy_delivered_wh
                        energy_kwh = Decimal(energy_wh) / Decimal('1000')
                        duration = None
                        if session.started_at:
                            duration = int((now - session.started_at).total_seconds())

                        session.meter_stop_wh = session.meter_start_wh + energy_wh
                        session.energy_delivered_kwh = energy_kwh.quantize(Decimal('0.001'))
                        session.status = ChargingSession.Status.FAULTED
                        session.stop_reason = 'OrphanCleanup'
                        session.stopped_at = now
                        session.duration_seconds = duration
                        session.save(update_fields=[
                            'meter_stop_wh', 'energy_delivered_kwh', 'status',
                            'stop_reason', 'stopped_at', 'duration_seconds', 'updated_at',
                        ])
                        BillingService.finalize_session_billing(session)

                    logger.info(
                        'Orphan cleanup: txn=%s finalized (%.3f kWh, %.2f ILS)',
                        session.transaction_id, energy_kwh, session.total_cost,
                    )
                except Exception:
                    logger.exception('Failed orphan cleanup for txn=%s', session.transaction_id)

        self.stdout.write(f'Orphaned sessions cleaned: {orphan_count}')

        # 3. Retry failed billing
        failed_sessions = ChargingSession.objects.select_related(
            'customer', 'customer__wallet',
        ).filter(
            billing_status=ChargingSession.BillingStatus.FAILED,
            customer__isnull=False,
        )

        retry_count = 0
        for session in failed_sessions:
            retry_count += 1
            remaining = session.total_cost - session.cost_deducted
            self.stdout.write(
                f'  Retry billing: txn={session.transaction_id} '
                f'remaining={remaining} ILS'
            )
            if not dry_run:
                try:
                    BillingService.finalize_session_billing(session)
                    if session.billing_status == ChargingSession.BillingStatus.BILLED:
                        logger.info('Billing retry succeeded for txn=%s', session.transaction_id)
                    else:
                        logger.warning('Billing retry still failed for txn=%s', session.transaction_id)
                except Exception:
                    logger.exception('Billing retry error for txn=%s', session.transaction_id)

        self.stdout.write(f'Failed billing retries: {retry_count}')

        self.stdout.write(self.style.SUCCESS('Cleanup complete'))
