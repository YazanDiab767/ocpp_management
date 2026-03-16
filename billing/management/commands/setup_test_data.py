from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import BillingPolicy, Tariff
from chargers.models import ChargePoint, Connector
from customers.models import Customer, Wallet
from customers.services import WalletService
from rfid.models import RFIDCard


class Command(BaseCommand):
    help = 'Create test data: customer, RFID card, wallet balance, charger, tariff, billing policy'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\nSetting up test data...\n'))

        # ── Tariff ──
        tariff, created = Tariff.objects.get_or_create(
            name='Standard Rate',
            defaults={
                'price_per_kwh': Decimal('1.2000'),
                'is_active': True,
                'description': 'Default tariff: 1.20 ILS per kWh',
            },
        )
        if not tariff.is_active:
            tariff.is_active = True
            tariff.save(update_fields=['is_active'])
        status = 'CREATED' if created else 'EXISTS'
        self.stdout.write(f'  [{status}] Tariff: {tariff.name} ({tariff.price_per_kwh} ILS/kWh)')

        # ── Billing Policy ──
        policy = BillingPolicy.load()
        self.stdout.write(f'  [READY]   Billing Policy: mode={policy.get_deduction_mode_display()}, '
                          f'min_balance={policy.minimum_balance_to_start} {policy.currency_code}')

        # ── Customer ──
        customer, created = Customer.objects.get_or_create(
            phone_number='0501234567',
            defaults={
                'first_name': 'Test',
                'last_name': 'Driver',
                'email': 'test@example.com',
                'vehicle_plate': '12-345-67',
                'notes': 'Test customer created by setup_test_data',
            },
        )
        if created:
            Wallet.objects.create(customer=customer)
        status = 'CREATED' if created else 'EXISTS'
        self.stdout.write(f'  [{status}] Customer: {customer.full_name} ({customer.phone_number})')

        # ── Wallet top-up ──
        wallet = customer.wallet
        if wallet.balance < Decimal('50.00'):
            topup_amount = Decimal('100.00') - wallet.balance
            if topup_amount > 0:
                WalletService.topup(
                    wallet_id=wallet.pk,
                    amount=topup_amount,
                    created_by=None,
                    description='Test data setup top-up',
                    receipt_number='TEST-001',
                )
                wallet.refresh_from_db()
                self.stdout.write(f'  [TOPUP]   Wallet topped up to {wallet.balance} ILS')
        else:
            self.stdout.write(f'  [READY]   Wallet balance: {wallet.balance} ILS')

        # ── RFID Card ──
        card, created = RFIDCard.objects.get_or_create(
            id_tag='TEST0001',
            defaults={
                'card_number': 'CARD-TEST-0001',
                'customer': customer,
                'status': RFIDCard.Status.ACTIVE,
                'notes': 'Test RFID card',
            },
        )
        if not created and (card.customer != customer or card.status != RFIDCard.Status.ACTIVE):
            card.customer = customer
            card.status = RFIDCard.Status.ACTIVE
            card.save(update_fields=['customer', 'status', 'updated_at'])
        status = 'CREATED' if created else 'EXISTS'
        self.stdout.write(f'  [{status}] RFID Card: id_tag={card.id_tag}, card={card.card_number}')

        # ── Charger ──
        cp, created = ChargePoint.objects.get_or_create(
            charge_point_id='SIM-CHARGER-001',
            defaults={
                'name': 'Simulator Charger #1',
                'vendor': 'SETEC',
                'model': 'Power 60kW',
                'max_power_kw': Decimal('60.00'),
                'location': 'Test Location',
                'is_active': True,
            },
        )
        if created:
            Connector.objects.create(
                charge_point=cp, connector_id=1,
                connector_type=Connector.ConnectorType.CCS2,
                max_power_kw=Decimal('60.00'),
            )
            Connector.objects.create(
                charge_point=cp, connector_id=2,
                connector_type=Connector.ConnectorType.CHADEMO,
                max_power_kw=Decimal('50.00'),
            )
        status = 'CREATED' if created else 'EXISTS'
        self.stdout.write(f'  [{status}] Charger: {cp.name} ({cp.charge_point_id})')

        # ── Summary ──
        wallet.refresh_from_db()
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(' Test data ready! Use these in the simulator:'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Charge Point ID : SIM-CHARGER-001')
        self.stdout.write(f'  RFID idTag      : TEST0001')
        self.stdout.write(f'  Customer        : {customer.full_name}')
        self.stdout.write(f'  Wallet Balance  : {wallet.balance} ILS')
        self.stdout.write(f'  Tariff          : {tariff.price_per_kwh} ILS/kWh')
        self.stdout.write(f'  Connector 1     : CCS-2 (DC 60kW)')
        self.stdout.write(f'  Connector 2     : CHAdeMO (DC 50kW)')
        self.stdout.write('')
        self.stdout.write('  Start server:    python manage.py runserver')
        self.stdout.write('  Run simulator:   python tools/charger_simulator.py')
        self.stdout.write('')
