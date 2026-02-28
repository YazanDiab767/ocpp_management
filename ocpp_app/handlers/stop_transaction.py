from ocpp_app.handlers.base import BaseHandler


class StopTransactionHandler(BaseHandler):
    action = 'StopTransaction'

    def handle(self, charge_point_id, payload, **kwargs):
        from sessions.services import SessionService

        transaction_id = payload.get('transactionId')
        meter_stop = payload.get('meterStop', 0)
        timestamp = payload.get('timestamp')
        id_tag = payload.get('idTag', '')
        reason = payload.get('reason', '')
        transaction_data = payload.get('transactionData')

        SessionService.stop_session(
            transaction_id=transaction_id,
            meter_stop=meter_stop,
            timestamp=timestamp,
            id_tag=id_tag,
            reason=reason,
            transaction_data=transaction_data,
        )

        result = {}
        if id_tag:
            result['idTagInfo'] = {'status': 'Accepted'}
        return result
