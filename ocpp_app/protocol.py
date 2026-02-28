"""
OCPP-J (JSON over WebSocket) message framing.
OCPP 1.6 uses JSON arrays:
  CALL:       [2, uniqueId, action, payload]
  CALLRESULT: [3, uniqueId, payload]
  CALLERROR:  [4, uniqueId, errorCode, errorDescription, errorDetails]
"""

CALL = 2
CALL_RESULT = 3
CALL_ERROR = 4


class OCPPMessageFrame:

    def __init__(self, message_type_id, unique_id, action=None, payload=None,
                 error_code=None, error_description=None, error_details=None):
        self.message_type_id = message_type_id
        self.unique_id = unique_id
        self.action = action
        self.payload = payload or {}
        self.error_code = error_code
        self.error_description = error_description
        self.error_details = error_details

    @classmethod
    def parse(cls, raw):
        if not isinstance(raw, list) or len(raw) < 3:
            raise ValueError(f'Invalid OCPP-J message format: expected list with 3+ elements')

        msg_type = raw[0]

        if msg_type == CALL:
            if len(raw) < 4:
                raise ValueError('CALL message requires 4 elements')
            return cls(
                message_type_id=CALL,
                unique_id=str(raw[1]),
                action=raw[2],
                payload=raw[3] if len(raw) > 3 else {},
            )
        elif msg_type == CALL_RESULT:
            return cls(
                message_type_id=CALL_RESULT,
                unique_id=str(raw[1]),
                payload=raw[2] if len(raw) > 2 else {},
            )
        elif msg_type == CALL_ERROR:
            return cls(
                message_type_id=CALL_ERROR,
                unique_id=str(raw[1]),
                error_code=raw[2] if len(raw) > 2 else '',
                error_description=raw[3] if len(raw) > 3 else '',
                error_details=raw[4] if len(raw) > 4 else {},
            )
        else:
            raise ValueError(f'Unknown OCPP message type: {msg_type}')

    @staticmethod
    def build_call_result(unique_id, payload):
        return [CALL_RESULT, unique_id, payload]

    @staticmethod
    def build_call(unique_id, action, payload):
        return [CALL, unique_id, action, payload]

    @staticmethod
    def build_call_error(unique_id, error_code, error_description='', error_details=None):
        return [CALL_ERROR, unique_id, error_code, error_description, error_details or {}]
