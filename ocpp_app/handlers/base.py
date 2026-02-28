class BaseHandler:
    """Base class for OCPP 1.6 message handlers."""

    action = ''

    def handle(self, charge_point_id, payload, **kwargs):
        raise NotImplementedError


class HandlerError(Exception):
    """Raised when a handler needs to return a CALLERROR."""

    def __init__(self, error_code, error_description='', error_details=None):
        self.error_code = error_code
        self.error_description = error_description
        self.error_details = error_details or {}
        super().__init__(error_description)
