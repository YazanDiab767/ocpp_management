import logging

from django.utils import timezone

from chargers.models import ChargePoint, Connector

logger = logging.getLogger('ocpp')


class ChargerService:

    @staticmethod
    def register_charge_point(charge_point_id, name, **kwargs):
        cp = ChargePoint.objects.create(
            charge_point_id=charge_point_id,
            name=name,
            **kwargs,
        )
        logger.info('Charge point registered: %s (%s)', name, charge_point_id)
        return cp

    @staticmethod
    def handle_boot(charge_point_id, vendor='', model='', serial_number='', firmware_version=''):
        """
        Called by BootNotification handler.
        Returns (charge_point, status_string).
        """
        try:
            cp = ChargePoint.objects.get(charge_point_id=charge_point_id)
        except ChargePoint.DoesNotExist:
            from django.conf import settings
            if getattr(settings, 'OCPP_ACCEPT_UNKNOWN_CHARGERS', False):
                cp = ChargePoint.objects.create(
                    charge_point_id=charge_point_id,
                    name=f'Auto-{charge_point_id}',
                    is_active=True,
                )
                logger.info('Auto-registered unknown charge point: %s', charge_point_id)
            else:
                logger.warning('BootNotification rejected: unknown charge point %s', charge_point_id)
                return None, 'Rejected'

        if not cp.is_active:
            logger.warning('BootNotification rejected: charge point %s is deactivated', charge_point_id)
            return cp, 'Rejected'

        cp.vendor = vendor or cp.vendor
        cp.model = model or cp.model
        cp.serial_number = serial_number or cp.serial_number
        cp.firmware_version = firmware_version or cp.firmware_version
        cp.status = ChargePoint.Status.ONLINE
        cp.last_boot = timezone.now()
        cp.last_heartbeat = timezone.now()
        cp.save(update_fields=[
            'vendor', 'model', 'serial_number', 'firmware_version',
            'status', 'last_boot', 'last_heartbeat', 'updated_at',
        ])

        logger.info('BootNotification accepted: %s (vendor=%s, model=%s)', charge_point_id, vendor, model)
        return cp, 'Accepted'

    @staticmethod
    def update_heartbeat(charge_point_id):
        updated = ChargePoint.objects.filter(charge_point_id=charge_point_id).update(
            last_heartbeat=timezone.now(),
            status=ChargePoint.Status.ONLINE,
        )
        if updated:
            logger.debug('Heartbeat from %s', charge_point_id)

    @staticmethod
    def update_connector_status(charge_point_id, connector_id, status,
                                 error_code='NoError', info='', timestamp=None):
        try:
            cp = ChargePoint.objects.get(charge_point_id=charge_point_id)
        except ChargePoint.DoesNotExist:
            logger.warning('StatusNotification for unknown charge point: %s', charge_point_id)
            return None

        ts = timezone.now()

        if connector_id == 0:
            if status == 'Faulted':
                cp.status = ChargePoint.Status.FAULTED
            elif status in ('Available', 'Charging', 'Preparing', 'Finishing'):
                cp.status = ChargePoint.Status.ONLINE
            cp.save(update_fields=['status', 'updated_at'])
            return None

        connector, created = Connector.objects.get_or_create(
            charge_point=cp,
            connector_id=connector_id,
            defaults={
                'ocpp_status': status,
                'error_code': error_code,
                'error_info': info,
                'last_status_update': ts,
            },
        )
        if not created:
            connector.ocpp_status = status
            connector.error_code = error_code
            connector.error_info = info
            connector.last_status_update = ts
            connector.save(update_fields=[
                'ocpp_status', 'error_code', 'error_info',
                'last_status_update', 'updated_at',
            ])

        if created:
            logger.info('Auto-discovered connector %d on %s', connector_id, charge_point_id)

        logger.debug(
            'StatusNotification: %s connector %d -> %s (error=%s)',
            charge_point_id, connector_id, status, error_code,
        )
        return connector

    @staticmethod
    def set_offline(charge_point_id):
        ChargePoint.objects.filter(charge_point_id=charge_point_id).update(
            status=ChargePoint.Status.OFFLINE,
        )
        logger.info('Charge point %s set to offline', charge_point_id)

    @staticmethod
    def get_charge_point_or_none(charge_point_id):
        try:
            return ChargePoint.objects.get(charge_point_id=charge_point_id)
        except ChargePoint.DoesNotExist:
            return None
