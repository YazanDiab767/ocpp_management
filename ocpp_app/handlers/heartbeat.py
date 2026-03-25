from datetime import datetime, timezone

from chargers.services import ChargerService
from ocpp_app.handlers.base import BaseHandler


class HeartbeatHandler(BaseHandler):
    action = 'Heartbeat'

    def handle(self, charge_point_id, payload, **kwargs):
        ChargerService.update_heartbeat(charge_point_id)
        return {
            'currentTime': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
