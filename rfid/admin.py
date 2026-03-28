from django.contrib import admin
from rfid.models import RFIDCard, RFIDTapLog


@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'id_tag', 'customer', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id_tag', 'card_number', 'customer__first_name', 'customer__last_name')
    raw_id_fields = ('customer',)


@admin.register(RFIDTapLog)
class RFIDTapLogAdmin(admin.ModelAdmin):
    list_display = ('id_tag', 'result', 'charge_point_id', 'customer_name', 'tapped_at')
    list_filter = ('result',)
    search_fields = ('id_tag', 'charge_point_id', 'customer_name')
    readonly_fields = ('id_tag', 'charge_point_id', 'result', 'rfid_card', 'customer_name', 'tapped_at')
