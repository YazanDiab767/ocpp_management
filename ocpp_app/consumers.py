import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from chargers.services import ChargerService
from ocpp_app.handlers.base import HandlerError
from ocpp_app.message_router import get_handler
from ocpp_app.protocol import CALL, CALL_ERROR, CALL_RESULT, OCPPMessageFrame
from ocpp_app.services import OCPPService

logger = logging.getLogger('ocpp')


class OCPPConsumer(WebsocketConsumer):
    """
    Django Channels WebSocket consumer for OCPP 1.6-J.
    URL: ws://<host>/ws/ocpp/<charge_point_id>/
    """

    def connect(self):
        self.charge_point_id = self.scope['url_route']['kwargs']['charge_point_id']
        self.group_name = f'cp_{self.charge_point_id}'

        requested_protocols = self.scope.get('subprotocols') or []

        if 'ocpp1.6' in requested_protocols:
            self.accept(subprotocol='ocpp1.6')
        else:
            logger.warning(
                'Charge point %s connected without ocpp1.6 subprotocol (got: %s)',
                self.charge_point_id, requested_protocols,
            )
            self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        logger.info('Charge point connected: %s', self.charge_point_id)

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name,
        )
        ChargerService.set_offline(self.charge_point_id)

        # Handle orphaned active sessions (power/internet outage)
        try:
            from sessions.services import SessionService
            SessionService.handle_charger_disconnect(self.charge_point_id)
        except Exception:
            logger.exception('Error handling orphaned sessions for %s', self.charge_point_id)

        logger.info('Charge point disconnected: %s (code=%s)', self.charge_point_id, close_code)

    def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            raw = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error('Invalid JSON from %s: %s', self.charge_point_id, text_data[:200])
            return

        # Log incoming message
        self._log_incoming(raw)

        try:
            msg = OCPPMessageFrame.parse(raw)
        except ValueError as e:
            logger.error('Failed to parse OCPP message from %s: %s', self.charge_point_id, e)
            return

        if msg.message_type_id == CALL:
            self._handle_call(msg)
        elif msg.message_type_id == CALL_RESULT:
            logger.info(
                'CallResult from %s for %s: %s',
                self.charge_point_id, msg.unique_id, msg.payload,
            )
        elif msg.message_type_id == CALL_ERROR:
            logger.warning(
                'CallError from %s for %s: %s - %s',
                self.charge_point_id, msg.unique_id,
                msg.error_code, msg.error_description,
            )

    def _handle_call(self, msg):
        handler = get_handler(msg.action)

        if handler is None:
            response = OCPPMessageFrame.build_call_error(
                msg.unique_id,
                'NotImplemented',
                f'Action {msg.action} is not supported',
            )
            self._send_ocpp(response)
            return

        try:
            result_payload = handler.handle(
                charge_point_id=self.charge_point_id,
                payload=msg.payload,
            )
            response = OCPPMessageFrame.build_call_result(msg.unique_id, result_payload)
        except HandlerError as e:
            response = OCPPMessageFrame.build_call_error(
                msg.unique_id, e.error_code, e.error_description, e.error_details,
            )
        except Exception as e:
            logger.exception('Error handling %s from %s', msg.action, self.charge_point_id)
            response = OCPPMessageFrame.build_call_error(
                msg.unique_id, 'InternalError', str(e),
            )

        self._send_ocpp(response)

    def _send_ocpp(self, message):
        text = json.dumps(message)
        OCPPService.log_message(
            charge_point_id=self.charge_point_id,
            direction='outgoing',
            message_type=message[0],
            unique_id=message[1],
            action=message[2] if message[0] == CALL and len(message) > 2 else '',
            payload=message[3] if message[0] == CALL and len(message) > 3
                    else message[2] if message[0] == CALL_RESULT else {},
        )
        self.send(text_data=text)

    def _log_incoming(self, raw):
        if not isinstance(raw, list) or len(raw) < 2:
            return
        msg_type = raw[0] if raw else 0
        unique_id = raw[1] if len(raw) > 1 else ''
        action = raw[2] if len(raw) > 2 and msg_type == CALL else ''
        payload = raw[3] if len(raw) > 3 and msg_type == CALL else (
            raw[2] if len(raw) > 2 and msg_type == CALL_RESULT else {}
        )
        OCPPService.log_message(
            charge_point_id=self.charge_point_id,
            direction='incoming',
            message_type=msg_type,
            unique_id=str(unique_id),
            action=action,
            payload=payload if isinstance(payload, dict) else {},
        )

    # Channel layer handler for server-to-charger commands
    def ocpp_send_call(self, event):
        message = OCPPMessageFrame.build_call(
            event['unique_id'], event['action'], event['payload'],
        )
        self._send_ocpp(message)
