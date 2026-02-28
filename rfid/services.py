import logging
from datetime import date

from django.utils import timezone

from rfid.models import RFIDCard

logger = logging.getLogger('ocpp')


class RFIDService:

    @staticmethod
    def register_card(id_tag, card_number, issued_by=None):
        card = RFIDCard.objects.create(
            id_tag=id_tag,
            card_number=card_number,
            status=RFIDCard.Status.UNASSIGNED,
            issued_by=issued_by,
            issued_at=timezone.now() if issued_by else None,
        )
        logger.info('RFID card registered: %s (id_tag=%s)', card_number, id_tag)
        return card

    @staticmethod
    def assign_to_customer(card_id, customer_id, issued_by=None):
        card = RFIDCard.objects.get(pk=card_id)
        card.customer_id = customer_id
        card.status = RFIDCard.Status.ACTIVE
        if issued_by:
            card.issued_by = issued_by
            card.issued_at = timezone.now()
        card.save(update_fields=['customer_id', 'status', 'issued_by', 'issued_at', 'updated_at'])
        logger.info('RFID card %s assigned to customer %s', card.card_number, customer_id)
        return card

    @staticmethod
    def unassign_card(card_id):
        card = RFIDCard.objects.get(pk=card_id)
        card.customer = None
        card.status = RFIDCard.Status.UNASSIGNED
        card.save(update_fields=['customer', 'status', 'updated_at'])
        return card

    @staticmethod
    def block_card(card_id):
        card = RFIDCard.objects.get(pk=card_id)
        card.status = RFIDCard.Status.BLOCKED
        card.save(update_fields=['status', 'updated_at'])
        logger.info('RFID card %s blocked', card.card_number)
        return card

    @staticmethod
    def activate_card(card_id):
        card = RFIDCard.objects.get(pk=card_id)
        if not card.customer:
            raise ValueError('Cannot activate card without a customer assignment')
        card.status = RFIDCard.Status.ACTIVE
        card.save(update_fields=['status', 'updated_at'])
        return card

    @staticmethod
    def authorize_id_tag(id_tag):
        """
        Core authorization method called by OCPP Authorize handler.
        Returns dict with 'status' matching OCPP AuthorizationStatus values:
        Accepted, Blocked, Expired, Invalid, ConcurrentTx
        """
        try:
            card = RFIDCard.objects.select_related('customer', 'customer__wallet').get(id_tag=id_tag)
        except RFIDCard.DoesNotExist:
            logger.warning('Authorization failed: unknown idTag %s', id_tag)
            return {'status': 'Invalid'}

        if card.status == RFIDCard.Status.BLOCKED:
            return {'status': 'Blocked'}

        if card.status == RFIDCard.Status.LOST:
            return {'status': 'Blocked'}

        if card.status == RFIDCard.Status.EXPIRED:
            return {'status': 'Expired'}

        if card.status == RFIDCard.Status.UNASSIGNED:
            return {'status': 'Invalid'}

        if card.expiry_date and card.expiry_date < date.today():
            card.status = RFIDCard.Status.EXPIRED
            card.save(update_fields=['status', 'updated_at'])
            return {'status': 'Expired'}

        if not card.customer:
            return {'status': 'Invalid'}

        if not card.customer.is_active:
            return {'status': 'Blocked'}

        result = {
            'status': 'Accepted',
        }
        if card.expiry_date:
            result['expiry_date'] = card.expiry_date.isoformat() + 'T00:00:00.000Z'

        return result

    @staticmethod
    def get_customer_for_id_tag(id_tag):
        try:
            card = RFIDCard.objects.select_related('customer', 'customer__wallet').get(
                id_tag=id_tag,
                status=RFIDCard.Status.ACTIVE,
            )
            return card.customer
        except RFIDCard.DoesNotExist:
            return None
