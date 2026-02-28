from ocpp_app.handlers.authorize import AuthorizeHandler
from ocpp_app.handlers.boot_notification import BootNotificationHandler
from ocpp_app.handlers.heartbeat import HeartbeatHandler
from ocpp_app.handlers.meter_values import MeterValuesHandler
from ocpp_app.handlers.start_transaction import StartTransactionHandler
from ocpp_app.handlers.status_notification import StatusNotificationHandler
from ocpp_app.handlers.stop_transaction import StopTransactionHandler

ACTION_HANDLERS = {
    'BootNotification': BootNotificationHandler(),
    'Heartbeat': HeartbeatHandler(),
    'Authorize': AuthorizeHandler(),
    'StartTransaction': StartTransactionHandler(),
    'StopTransaction': StopTransactionHandler(),
    'MeterValues': MeterValuesHandler(),
    'StatusNotification': StatusNotificationHandler(),
}


def get_handler(action):
    return ACTION_HANDLERS.get(action)
