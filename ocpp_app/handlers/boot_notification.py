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

        # Finalize any orphaned sessions from before reboot
        try:
            from sessions.services import SessionService
            SessionService.handle_charger_disconnect(charge_point_id)
        except Exception:
            logger.exception('Error cleaning up sessions on boot for %s', charge_point_id)

        cp, status = ChargerService.handle_boot(
            charge_point_id=charge_point_id,
            vendor=vendor,
            model=model,
            serial_number=serial,
            firmware_version=firmware,
        )

        interval = cp.heartbeat_interval if cp else 300

        return {
            'currentTime': datetime.now(timezone.utc).isoformat(),
            'interval': interval,
            'status': status,
        }
