from django.contrib import admin
from rfid.models import RFIDCard


@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'id_tag', 'customer', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id_tag', 'card_number', 'customer__first_name', 'customer__last_name')
    raw_id_fields = ('customer',)
