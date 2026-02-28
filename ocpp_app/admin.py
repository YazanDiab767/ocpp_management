from django.contrib import admin
from ocpp_app.models import OCPPMessage


@admin.register(OCPPMessage)
class OCPPMessageAdmin(admin.ModelAdmin):
    list_display = ('charge_point_id', 'direction', 'message_type', 'action', 'created_at')
    list_filter = ('direction', 'action')
    search_fields = ('charge_point_id', 'action')
    readonly_fields = ('payload',)
