import uuid
from decimal import Decimal

from django.db import models


class ChargingSession(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        FAULTED = 'faulted', 'Faulted'
        INVALID = 'invalid', 'Invalid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.IntegerField(unique=True, db_index=True)

    charge_point = models.ForeignKey(
        'chargers.ChargePoint',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions',
    )
    connector = models.ForeignKey(
        'chargers.Connector',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sessions',
    )
    rfid_card = models.ForeignKey(
        'rfid.RFIDCard',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sessions',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sessions',
    )
    id_tag = models.CharField(max_length=20, blank=True, default='')
    charge_point_id_str = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Denormalized charge_point_id for fast querying',
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Meter readings (in Wh as reported by charger)
    meter_start_wh = models.IntegerField(default=0)
    meter_stop_wh = models.IntegerField(null=True, blank=True)
    energy_delivered_wh = models.IntegerField(
        default=0,
        help_text='Computed: meter_stop - meter_start (or latest meter value - start)',
    )
    energy_delivered_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000'),
    )

    # Billing snapshot
    tariff_per_kwh = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text='Snapshot of tariff at session start',
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    cost_deducted = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Amount already deducted from wallet (for real-time mode)',
    )

    stop_reason = models.CharField(max_length=50, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'charging_sessions'
        db_table = 'sessions_charging_session'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['charge_point_id_str', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['id_tag']),
        ]

    def __str__(self):
        return f'Session {self.transaction_id} ({self.get_status_display()})'


class MeterValue(models.Model):

    session = models.ForeignKey(
        ChargingSession,
        on_delete=models.CASCADE,
        related_name='meter_values',
    )
    connector = models.ForeignKey(
        'chargers.Connector',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    timestamp = models.DateTimeField()

    measurand = models.CharField(
        max_length=50,
        default='Energy.Active.Import.Register',
        help_text='OCPP measurand name',
    )
    value = models.CharField(max_length=50)
    unit = models.CharField(max_length=10, default='Wh')
    phase = models.CharField(max_length=10, blank=True, default='')
    context = models.CharField(max_length=30, blank=True, default='Sample.Periodic')
    location = models.CharField(max_length=10, blank=True, default='Outlet')
    format = models.CharField(max_length=10, blank=True, default='Raw')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'charging_sessions'
        db_table = 'sessions_meter_value'
        ordering = ['session', 'timestamp']
        indexes = [
            models.Index(fields=['session', 'measurand', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.measurand}: {self.value} {self.unit}'
