from django.contrib import admin

from billing.models import BillingPolicy, Tariff


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_kwh', 'is_active', 'effective_from', 'effective_until')
    list_filter = ('is_active',)


@admin.register(BillingPolicy)
class BillingPolicyAdmin(admin.ModelAdmin):
    list_display = ('deduction_mode', 'minimum_balance_to_start', 'auto_stop_balance_threshold', 'currency_code')
