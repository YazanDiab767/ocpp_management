from django.contrib import admin
from chargers.models import ChargePoint, Connector


class ConnectorInline(admin.TabularInline):
    model = Connector
    extra = 0


@admin.register(ChargePoint)
class ChargePointAdmin(admin.ModelAdmin):
    list_display = ('name', 'charge_point_id', 'status', 'is_active', 'last_heartbeat')
    list_filter = ('status', 'is_active')
    search_fields = ('name', 'charge_point_id', 'vendor')
    inlines = [ConnectorInline]


@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('charge_point', 'connector_id', 'connector_type', 'ocpp_status', 'error_code')
    list_filter = ('ocpp_status', 'connector_type')
