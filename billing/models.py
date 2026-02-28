from decimal import Decimal

from django.db import models


class Tariff(models.Model):

    name = models.CharField(max_length=100, help_text='E.g. Standard Rate, Night Rate')
    price_per_kwh = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text='Price per kWh in configured currency',
    )
    is_active = models.BooleanField(default=False)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_until = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_tariff'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f'{self.name} ({self.price_per_kwh} ILS/kWh)'


class BillingPolicy(models.Model):
    """
    Singleton billing configuration. Always use pk=1.
    """

    class DeductionMode(models.TextChoices):
        END_OF_SESSION = 'end_of_session', 'End of Session'
        REAL_TIME = 'real_time', 'Real-time (deduct on each MeterValues)'

    deduction_mode = models.CharField(
        max_length=20,
        choices=DeductionMode.choices,
        default=DeductionMode.END_OF_SESSION,
    )
    minimum_balance_to_start = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text='Minimum wallet balance required to start a session',
    )
    auto_stop_balance_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Auto-stop session when balance falls to this amount',
    )
    allow_negative_balance = models.BooleanField(
        default=False,
        help_text='If True, session continues even if balance goes negative',
    )
    currency_code = models.CharField(max_length=5, default='ILS')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'billing_policy'
        verbose_name = 'Billing Policy'
        verbose_name_plural = 'Billing Policies'

    def __str__(self):
        return f'Billing Policy (mode={self.get_deduction_mode_display()})'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
