import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import BillingPolicy, Tariff
from customers.services import WalletService

logger = logging.getLogger('ocpp')


class TariffService:

    @staticmethod
    def get_active_tariff():
        return Tariff.objects.filter(is_active=True).first()

    @staticmethod
    def get_active_price_per_kwh():
        tariff = TariffService.get_active_tariff()
        if tariff:
            return tariff.price_per_kwh
        return Decimal('0.0000')

    @staticmethod
    def create_tariff(*, name, price_per_kwh, activate=False, **kwargs):
        with transaction.atomic():
            if activate:
                Tariff.objects.filter(is_active=True).update(is_active=False)
            tariff = Tariff.objects.create(
                name=name,
                price_per_kwh=Decimal(str(price_per_kwh)),
                is_active=activate,
                **kwargs,
            )
        return tariff

    @staticmethod
    def activate_tariff(tariff_id):
        with transaction.atomic():
            Tariff.objects.filter(is_active=True).update(is_active=False)
            Tariff.objects.filter(pk=tariff_id).update(is_active=True)


class BillingService:

    @staticmethod
    def calculate_cost(energy_kwh, tariff_per_kwh):
        return (Decimal(str(energy_kwh)) * Decimal(str(tariff_per_kwh))).quantize(Decimal('0.01'))

    @staticmethod
    def check_can_start(wallet_id):
        policy = BillingPolicy.load()
        balance = WalletService.get_balance(wallet_id)
        if balance >= policy.minimum_balance_to_start:
            return True, ''
        return False, (
            f'Insufficient balance ({balance} {policy.currency_code}). '
            f'Minimum required: {policy.minimum_balance_to_start} {policy.currency_code}'
        )

    @staticmethod
    def process_realtime_deduction(session):
        """
        Called during MeterValues in real-time deduction mode.
        Deducts the incremental cost since last deduction.
        """
        policy = BillingPolicy.load()
        if policy.deduction_mode != BillingPolicy.DeductionMode.REAL_TIME:
            return

        if not session.customer:
            return

        total_cost = BillingService.calculate_cost(
            session.energy_delivered_kwh, session.tariff_per_kwh,
        )
        amount_to_deduct = total_cost - session.cost_deducted

        if amount_to_deduct <= 0:
            return

        try:
            wallet = session.customer.wallet
            WalletService.deduct(
                wallet_id=wallet.pk,
                amount=amount_to_deduct,
                reference_type='charging_session',
                reference_id=str(session.pk),
                description=f'Real-time charge: session {session.transaction_id}',
            )
            session.cost_deducted += amount_to_deduct
            session.total_cost = total_cost
            session.save(update_fields=['cost_deducted', 'total_cost', 'updated_at'])
            logger.info(
                'Real-time deduction: %.2f ILS for session %s (total deducted: %.2f)',
                amount_to_deduct, session.transaction_id, session.cost_deducted,
            )
        except Exception:
            logger.exception('Failed real-time deduction for session %s', session.transaction_id)

    @staticmethod
    def finalize_session_billing(session):
        """
        Called at session end. For end-of-session mode, deducts the full cost.
        For real-time mode, deducts any remaining difference.
        Sets billing_status to track success/failure for retry.
        """
        from sessions.models import ChargingSession

        if not session.customer:
            logger.warning('No customer for session %s, skipping billing', session.transaction_id)
            session.billing_status = ChargingSession.BillingStatus.NOT_APPLICABLE
            session.total_cost = BillingService.calculate_cost(
                session.energy_delivered_kwh, session.tariff_per_kwh,
            )
            session.save(update_fields=['billing_status', 'total_cost', 'updated_at'])
            return

        total_cost = BillingService.calculate_cost(
            session.energy_delivered_kwh, session.tariff_per_kwh,
        )
        remaining = total_cost - session.cost_deducted

        if remaining > 0:
            try:
                wallet = session.customer.wallet
                WalletService.deduct(
                    wallet_id=wallet.pk,
                    amount=remaining,
                    reference_type='charging_session',
                    reference_id=str(session.pk),
                    description=f'Charging session {session.transaction_id} finalized',
                )
                session.cost_deducted += remaining
                session.billing_status = ChargingSession.BillingStatus.BILLED
            except Exception:
                logger.exception('Failed final deduction for session %s', session.transaction_id)
                session.billing_status = ChargingSession.BillingStatus.FAILED
        else:
            # All already deducted in real-time mode
            session.billing_status = ChargingSession.BillingStatus.BILLED

        session.total_cost = total_cost
        session.save(update_fields=['total_cost', 'cost_deducted', 'billing_status', 'updated_at'])
        logger.info(
            'Session %s billing finalized: %.2f ILS (%.3f kWh @ %.4f ILS/kWh) billing_status=%s',
            session.transaction_id, total_cost,
            session.energy_delivered_kwh, session.tariff_per_kwh,
            session.billing_status,
        )

    @staticmethod
    def should_auto_stop(session):
        """
        Returns True if the session should be auto-stopped due to low balance.
        """
        policy = BillingPolicy.load()
        if policy.allow_negative_balance:
            return False
        if not session.customer:
            return False

        balance = WalletService.get_balance(session.customer.wallet.pk)
        return balance <= policy.auto_stop_balance_threshold
