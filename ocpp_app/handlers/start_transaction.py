from ocpp_app.handlers.base import BaseHandler


class StartTransactionHandler(BaseHandler):
    action = 'StartTransaction'

    def handle(self, charge_point_id, payload, **kwargs):
        # Import here to avoid circular imports at module load
        from sessions.services import SessionService

        connector_id = payload.get('connectorId')
        id_tag = payload.get('idTag', '')
        meter_start = payload.get('meterStart', 0)
        timestamp = payload.get('timestamp')

        transaction_id, id_tag_info = SessionService.start_session(
            charge_point_id=charge_point_id,
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            timestamp=timestamp,
        )

        return {
            'transactionId': transaction_id,
            'idTagInfo': id_tag_info,
        }
