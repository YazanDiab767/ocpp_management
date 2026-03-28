from django.conf import settings
from django.db import models


class RFIDTapLog(models.Model):
    """Records every RFID card tap on any charger, regardless of outcome."""

    class Result(models.TextChoices):
        ACCEPTED = 'Accepted', 'Accepted'
        BLOCKED = 'Blocked', 'Blocked'
        EXPIRED = 'Expired', 'Expired'
        INVALID = 'Invalid', 'Invalid'
        CONCURRENT_TX = 'ConcurrentTx', 'Concurrent Transaction'

    id_tag = models.CharField(max_length=20, db_index=True)
    charge_point_id = models.CharField(max_length=100, blank=True, default='')
    result = models.CharField(max_length=20, choices=Result.choices)
    rfid_card = models.ForeignKey(
        'RFIDCard',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tap_logs',
    )
    customer_name = models.CharField(max_length=200, blank=True, default='')
    tapped_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'rfid_tap_log'
        ordering = ['-tapped_at']
        verbose_name = 'RFID Tap Log'
        verbose_name_plural = 'RFID Tap Logs'

    def __str__(self):
        return f'{self.id_tag} - {self.result} @ {self.tapped_at:%Y-%m-%d %H:%M}'


class RFIDCard(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        BLOCKED = 'blocked', 'Blocked'
        LOST = 'lost', 'Lost'
        EXPIRED = 'expired', 'Expired'
        UNASSIGNED = 'unassigned', 'Unassigned'

    id_tag = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text='RFID card UID as reported by charger (OCPP idTag)',
    )
    card_number = models.CharField(
        max_length=50, unique=True,
        help_text='Human-readable card number printed on the card',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rfid_cards',
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.UNASSIGNED,
    )
    expiry_date = models.DateField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='issued_cards',
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rfid_card'
        verbose_name = 'RFID Card'
        verbose_name_plural = 'RFID Cards'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f'RFID {self.card_number} ({self.get_status_display()})'
