from django import forms

from chargers.models import ChargePoint, Connector


class ChargePointForm(forms.ModelForm):
    class Meta:
        model = ChargePoint
        fields = [
            'charge_point_id', 'name', 'vendor', 'model', 'serial_number',
            'location', 'latitude', 'longitude', 'max_power_kw',
            'heartbeat_interval', 'is_active', 'notes',
        ]
        widgets = {
            'charge_point_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'max_power_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'heartbeat_interval': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ConnectorForm(forms.ModelForm):
    class Meta:
        model = Connector
        fields = ['connector_id', 'connector_type', 'max_power_kw']
        widgets = {
            'connector_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'connector_type': forms.Select(attrs={'class': 'form-select'}),
            'max_power_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
