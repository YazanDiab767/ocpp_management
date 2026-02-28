import uuid

from django.db import models


class OCPPMessage(models.Model):

    class Direction(models.TextChoices):
        INCOMING = 'incoming', 'Incoming (CP -> Server)'
        OUTGOING = 'outgoing', 'Outgoing (Server -> CP)'

    class MessageType(models.IntegerChoices):
        CALL = 2, 'Call'
        CALL_RESULT = 3, 'CallResult'
        CALL_ERROR = 4, 'CallError'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charge_point_id = models.CharField(max_length=50, db_index=True)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    message_type = models.IntegerField(choices=MessageType.choices)
    unique_id = models.CharField(max_length=36, help_text='OCPP message unique ID')
    action = models.CharField(max_length=36, blank=True, default='')
    payload = models.JSONField(default=dict)
    error_code = models.CharField(max_length=50, blank=True, default='')
    error_description = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ocpp_message'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['charge_point_id', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f'{self.direction} {self.action} ({self.charge_point_id})'
