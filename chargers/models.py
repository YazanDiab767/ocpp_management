import uuid

from django.db import models


class ChargePoint(models.Model):

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        FAULTED = 'faulted', 'Faulted'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charge_point_id = models.CharField(
        max_length=50, unique=True, db_index=True,
        help_text='Charge Box Identity, e.g. CBI-146b9c8cceca',
    )
    name = models.CharField(max_length=100, help_text='Display name, e.g. Haifa Station #1')
    vendor = models.CharField(max_length=50, blank=True, default='')
    model = models.CharField(max_length=50, blank=True, default='')
    serial_number = models.CharField(max_length=50, blank=True, default='')
    firmware_version = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=200, blank=True, default='', help_text='Address or description')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OFFLINE)
    max_power_kw = models.DecimalField(max_digits=7, decimal_places=2, default=60)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_boot = models.DateTimeField(null=True, blank=True)
    heartbeat_interval = models.IntegerField(default=300, help_text='Heartbeat interval in seconds')
    is_active = models.BooleanField(default=True, help_text='If False, BootNotification returns Rejected')
    boot_enforce_config = models.TextField(
        blank=True, default='',
        help_text='OCPP configuration keys to enforce on every boot. One KEY=VALUE per line. '
                  'Example: StopTransactionOnInvalidId=true',
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chargers_charge_point'
        verbose_name = 'Charge Point'
        verbose_name_plural = 'Charge Points'

    def __str__(self):
        return f'{self.name} ({self.charge_point_id})'


class Connector(models.Model):

    class ConnectorType(models.TextChoices):
        CCS1 = 'ccs1', 'CCS-1 (DC)'
        CCS2 = 'ccs2', 'CCS-2 (DC)'
        CHADEMO = 'chademo', 'CHAdeMO (DC)'
        TYPE2 = 'type2', 'Type 2 (AC)'
        TYPE1 = 'type1', 'Type 1 (AC)'

    class OCPPStatus(models.TextChoices):
        AVAILABLE = 'Available', 'Available'
        PREPARING = 'Preparing', 'Preparing'
        CHARGING = 'Charging', 'Charging'
        SUSPENDED_EV = 'SuspendedEV', 'Suspended EV'
        SUSPENDED_EVSE = 'SuspendedEVSE', 'Suspended EVSE'
        FINISHING = 'Finishing', 'Finishing'
        RESERVED = 'Reserved', 'Reserved'
        UNAVAILABLE = 'Unavailable', 'Unavailable'
        FAULTED = 'Faulted', 'Faulted'

    charge_point = models.ForeignKey(
        ChargePoint,
        on_delete=models.CASCADE,
        related_name='connectors',
    )
    connector_id = models.PositiveSmallIntegerField(
        help_text='OCPP connector ID. 1-based. 0 = charge point itself.',
    )
    connector_type = models.CharField(
        max_length=10,
        choices=ConnectorType.choices,
        blank=True, default='',
    )
    ocpp_status = models.CharField(
        max_length=15,
        choices=OCPPStatus.choices,
        default=OCPPStatus.AVAILABLE,
    )
    error_code = models.CharField(max_length=30, default='NoError')
    error_info = models.CharField(max_length=255, blank=True, default='')
    max_power_kw = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    last_status_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chargers_connector'
        unique_together = [('charge_point', 'connector_id')]
        ordering = ['charge_point', 'connector_id']
        indexes = [
            models.Index(fields=['ocpp_status']),
        ]

    def __str__(self):
        return f'{self.charge_point.name} / Connector {self.connector_id}'
