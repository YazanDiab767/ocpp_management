from chargers.services import ChargerService
from ocpp_app.handlers.base import BaseHandler


class StatusNotificationHandler(BaseHandler):
    action = 'StatusNotification'

    def handle(self, charge_point_id, payload, **kwargs):
        connector_id = payload.get('connectorId', 0)
        status = payload.get('status', '')
        error_code = payload.get('errorCode', 'NoError')
        info = payload.get('info', '')
        timestamp = payload.get('timestamp')

        ChargerService.update_connector_status(
            charge_point_id=charge_point_id,
            connector_id=connector_id,
            status=status,
            error_code=error_code,
            info=info,
            timestamp=timestamp,
        )

        return {}
