import logging
from decimal import Decimal

from django.db import transaction

from customers.models import Customer, Wallet, WalletTransaction

logger = logging.getLogger('ocpp')


class CustomerService:

    @staticmethod
    def create_customer(*, created_by, **kwargs):
        with transaction.atomic():
            customer = Customer.objects.create(created_by=created_by, **kwargs)
            Wallet.objects.create(customer=customer)
        return customer

    @staticmethod
    def get_customer(customer_id):
        return Customer.objects.select_related('wallet').get(pk=customer_id)

    @staticmethod
    def search_customers(query='', is_active=None):
        qs = Customer.objects.select_related('wallet').all()
        if query:
            qs = qs.filter(
                models.Q(first_name__icontains=query)
                | models.Q(last_name__icontains=query)
                | models.Q(phone_number__icontains=query)
            )
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs


class WalletService:

    @staticmethod
    def topup(wallet_id, amount, created_by, description='', receipt_number=''):
        if amount <= 0:
            raise ValueError('Top-up amount must be positive')

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
            balance_before = wallet.balance
            wallet.balance += Decimal(str(amount))
            wallet.save(update_fields=['balance', 'updated_at'])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.TOPUP,
                amount=Decimal(str(amount)),
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                receipt_number=receipt_number,
                reference_type='manual',
                created_by=created_by,
            )
            logger.info(
                'Wallet %s topped up by %s ILS (by user %s)',
                wallet_id, amount, created_by,
            )
            return txn

    @staticmethod
    def deduct(wallet_id, amount, reference_type='', reference_id='',
               description='', created_by=None):
        if amount <= 0:
            raise ValueError('Deduction amount must be positive')

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
            balance_before = wallet.balance
            wallet.balance -= Decimal(str(amount))
            wallet.save(update_fields=['balance', 'updated_at'])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.CHARGE_DEDUCTION,
                amount=-Decimal(str(amount)),
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
                created_by=created_by,
            )
            logger.info(
                'Wallet %s deducted %s ILS (ref: %s/%s)',
                wallet_id, amount, reference_type, reference_id,
            )
            return txn

    @staticmethod
    def adjust(wallet_id, amount, created_by, description=''):
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
            balance_before = wallet.balance
            wallet.balance += Decimal(str(amount))
            wallet.save(update_fields=['balance', 'updated_at'])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.ADJUSTMENT,
                amount=Decimal(str(amount)),
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description,
                reference_type='manual',
                created_by=created_by,
            )
            return txn

    @staticmethod
    def get_balance(wallet_id):
        return Wallet.objects.get(pk=wallet_id).balance

    @staticmethod
    def check_sufficient_balance(wallet_id, minimum):
        balance = Wallet.objects.get(pk=wallet_id).balance
        return balance >= Decimal(str(minimum))
