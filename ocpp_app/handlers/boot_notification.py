import logging
from datetime import datetime, timezone

from chargers.services import ChargerService
from ocpp_app.handlers.base import BaseHandler

logger = logging.getLogger('ocpp')


class BootNotificationHandler(BaseHandler):
    action = 'BootNotification'

    def handle(self, charge_point_id, payload, **kwargs):
        vendor = payload.get('chargePointVendor', '')
        model = payload.get('chargePointModel', '')
        serial = payload.get('chargePointSerialNumber', '')
        firmware = payload.get('firmwareVersion', '')

        # Reactivate sessions that were faulted by a recent server restart
        # (disconnect handler marks them as faulted, but charger is still charging)
        try:
            from sessions.services import SessionService
            SessionService.reactivate_on_reconnect(charge_point_id)
        except Exception:
            logger.exception('Error reactivating sessions on boot for %s', charge_point_id)

        cp, status = ChargerService.handle_boot(
            charge_point_id=charge_point_id,
            vendor=vendor,
            model=model,
            serial_number=serial,
            firmware_version=firmware,
        )

        interval = cp.heartbeat_interval if cp else 300

        # Auto-enforce configured OCPP keys on every boot
        if cp and cp.boot_enforce_config and status == 'Accepted':
            try:
                from ocpp_app.services import OCPPService
                for line in cp.boot_enforce_config.splitlines():
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, _, value = line.partition('=')
                        key, value = key.strip(), value.strip()
                        if key and value:
                            OCPPService.send_change_configuration(charge_point_id, key, value)
                            logger.info('Auto-enforced config on boot: %s=%s → %s', key, value, charge_point_id)
            except Exception:
                logger.exception('Error auto-enforcing boot configs for %s', charge_point_id)

        return {
            'currentTime': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'interval': interval,
            'status': status,
        }
