from django import forms

from sessions.models import ChargingSession


class SessionFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Statuses')] + list(ChargingSession.Status.choices)

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    charge_point_id = forms.CharField(max_length=50, required=False, label='Charger ID')
    customer_search = forms.CharField(max_length=100, required=False, label='Customer')
