from ocpp_app.handlers.base import BaseHandler
from rfid.services import RFIDService


class AuthorizeHandler(BaseHandler):
    action = 'Authorize'

    def handle(self, charge_point_id, payload, **kwargs):
        id_tag = payload.get('idTag', '')
        auth_result = RFIDService.authorize_id_tag(id_tag)

        id_tag_info = {'status': auth_result['status']}
        if auth_result.get('expiry_date'):
            id_tag_info['expiryDate'] = auth_result['expiry_date']

        return {'idTagInfo': id_tag_info}
