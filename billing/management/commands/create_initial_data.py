from decimal import Decimal

from django.core.management.base import BaseCommand

from billing.models import BillingPolicy, Tariff


class Command(BaseCommand):
    help = 'Create default tariff (1.20 ILS/kWh) and billing policy'

    def handle(self, *args, **options):
        # Create default tariff
        tariff, created = Tariff.objects.get_or_create(
            name='Standard Rate',
            defaults={
                'price_per_kwh': Decimal('1.2000'),
                'is_active': True,
                'description': 'Default tariff: 1.20 ILS per kWh',
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created default tariff: {tariff.name} ({tariff.price_per_kwh} ILS/kWh)'
            ))
        else:
            self.stdout.write(f'Default tariff already exists: {tariff.name}')

        # Create billing policy singleton
        policy = BillingPolicy.load()
        self.stdout.write(self.style.SUCCESS(
            f'Billing policy ready: mode={policy.get_deduction_mode_display()}, '
            f'min_balance={policy.minimum_balance_to_start} {policy.currency_code}'
        ))
