import logging
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ocpp_app.models import OCPPMessage

logger = logging.getLogger('ocpp')


class OCPPService:

    @staticmethod
    def log_message(charge_point_id, direction, message_type, unique_id,
                    action='', payload=None, error_code='', error_description=''):
        try:
            OCPPMessage.objects.create(
                charge_point_id=charge_point_id,
                direction=direction,
                message_type=message_type,
                unique_id=unique_id,
                action=action,
                payload=payload or {},
                error_code=error_code,
                error_description=error_description,
            )
        except Exception:
            logger.exception('Failed to log OCPP message for %s', charge_point_id)

    @staticmethod
    def send_remote_stop(charge_point_id, transaction_id):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'RemoteStopTransaction',
            'payload': {'transactionId': transaction_id},
        })
        logger.info(
            'Sent RemoteStopTransaction to %s (txn=%s)',
            charge_point_id, transaction_id,
        )

    @staticmethod
    def send_remote_start(charge_point_id, connector_id, id_tag):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'RemoteStartTransaction',
            'payload': {
                'connectorId': connector_id,
                'idTag': id_tag,
            },
        })

    @staticmethod
    def send_reset(charge_point_id, reset_type='Soft'):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'Reset',
            'payload': {'type': reset_type},
        })

    @staticmethod
    def send_trigger_message(charge_point_id, requested_message, connector_id=None):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        payload = {'requestedMessage': requested_message}
        if connector_id is not None:
            payload['connectorId'] = connector_id

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'TriggerMessage',
            'payload': payload,
        })
        logger.info(
            'Sent TriggerMessage (%s) to %s',
            requested_message, charge_point_id,
        )

    @staticmethod
    def send_get_configuration(charge_point_id, keys=None):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        payload = {}
        if keys:
            payload['key'] = keys

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'GetConfiguration',
            'payload': payload,
        })
        logger.info('Sent GetConfiguration to %s', charge_point_id)

    @staticmethod
    def send_change_configuration(charge_point_id, key, value):
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'ChangeConfiguration',
            'payload': {'key': key, 'value': value},
        })
        logger.info(
            'Sent ChangeConfiguration to %s: %s=%s',
            charge_point_id, key, value,
        )

    @staticmethod
    def send_change_availability(charge_point_id, connector_id, availability_type):
        """
        Send ChangeAvailability to a specific connector.
        availability_type must be 'Operative' or 'Inoperative'.
        Use connector_id=0 to affect the entire charge point.
        """
        channel_layer = get_channel_layer()
        group_name = f'cp_{charge_point_id}'
        msg_id = str(uuid.uuid4())

        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'ocpp.send_call',
            'unique_id': msg_id,
            'action': 'ChangeAvailability',
            'payload': {
                'connectorId': connector_id,
                'type': availability_type,
            },
        })
        logger.info(
            'Sent ChangeAvailability to %s connector %d: %s',
            charge_point_id, connector_id, availability_type,
        )
