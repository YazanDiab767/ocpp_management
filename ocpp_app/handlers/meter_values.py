from ocpp_app.handlers.base import BaseHandler


class MeterValuesHandler(BaseHandler):
    action = 'MeterValues'

    def handle(self, charge_point_id, payload, **kwargs):
        from sessions.services import SessionService

        connector_id = payload.get('connectorId')
        transaction_id = payload.get('transactionId')
        meter_values = payload.get('meterValue', [])

        SessionService.update_meter_values(
            connector_id_ocpp=connector_id,
            charge_point_id=charge_point_id,
            transaction_id=transaction_id,
            meter_values_payload=meter_values,
        )

        return {}
