from django import forms

from billing.models import BillingPolicy, Tariff


class TariffForm(forms.ModelForm):
    activate = forms.BooleanField(
        required=False,
        help_text='Set this tariff as the active tariff (deactivates the current one)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Tariff
        fields = ['name', 'price_per_kwh', 'effective_from', 'effective_until', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price_per_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'effective_from': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'effective_until': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class BillingPolicyForm(forms.ModelForm):

    class Meta:
        model = BillingPolicy
        fields = [
            'deduction_mode',
            'minimum_balance_to_start',
            'auto_stop_balance_threshold',
            'allow_negative_balance',
            'currency_code',
        ]
        widgets = {
            'deduction_mode': forms.Select(attrs={'class': 'form-select'}),
            'minimum_balance_to_start': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'auto_stop_balance_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allow_negative_balance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
