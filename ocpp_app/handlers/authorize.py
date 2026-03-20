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

        id_tag_info = {'status': auth_result['status']}
        if auth_result.get('expiry_date'):
            id_tag_info['expiryDate'] = auth_result['expiry_date']

        return {'idTagInfo': id_tag_info}
