from django.contrib import admin
from customers.models import CarMake, Customer, Wallet, WalletTransaction


@admin.register(CarMake)
class CarMakeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'vehicle_make', 'is_active', 'created_at')
    list_filter = ('is_active', 'vehicle_make')
    search_fields = ('first_name', 'last_name', 'phone_number')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('customer', 'balance', 'updated_at')
    raw_id_fields = ('customer',)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type',)
    raw_id_fields = ('wallet',)
