from django.contrib import admin

from sessions.models import ChargingSession, MeterValue


class MeterValueInline(admin.TabularInline):
    model = MeterValue
    extra = 0
    readonly_fields = ('timestamp', 'measurand', 'value', 'unit', 'context')


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'charge_point_id_str', 'id_tag', 'status',
        'energy_delivered_kwh', 'total_cost', 'started_at', 'stopped_at',
    )
    list_filter = ('status',)
    search_fields = ('transaction_id', 'charge_point_id_str', 'id_tag')
    readonly_fields = ('id', 'transaction_id')
    inlines = [MeterValueInline]


@admin.register(MeterValue)
class MeterValueAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'measurand', 'value', 'unit')
    list_filter = ('measurand',)
