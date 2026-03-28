import logging

from ocpp_app.handlers.base import BaseHandler
from rfid.services import RFIDService

logger = logging.getLogger('ocpp')


class AuthorizeHandler(BaseHandler):
    action = 'Authorize'

    def handle(self, charge_point_id, payload, **kwargs):
        id_tag = payload.get('idTag', '')
        logger.info('>>> RFID card tapped on %s — idTag: %s', charge_point_id, id_tag)
        auth_result = RFIDService.authorize_id_tag(id_tag)
        logger.info('>>> Authorize result for idTag %s: %s', id_tag, auth_result['status'])

        # Log every tap attempt
        try:
            from rfid.models import RFIDCard, RFIDTapLog
            rfid_card = None
            customer_name = ''
            try:
                rfid_card = RFIDCard.objects.select_related('customer').get(id_tag=id_tag)
                if rfid_card.customer:
                    customer_name = rfid_card.customer.full_name
            except RFIDCard.DoesNotExist:
                pass
            RFIDTapLog.objects.create(
                id_tag=id_tag,
                charge_point_id=charge_point_id,
                result=auth_result['status'],
                rfid_card=rfid_card,
                customer_name=customer_name,
            )
        except Exception:
            logger.exception('Failed to log RFID tap for idTag %s', id_tag)

        id_tag_info = {'status': auth_result['status']}
        if auth_result.get('expiry_date'):
            id_tag_info['expiryDate'] = auth_result['expiry_date']

        return {'idTagInfo': id_tag_info}
