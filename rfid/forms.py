from django import forms

from customers.models import Customer
from rfid.models import RFIDCard


class RFIDCardCreateForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Leave empty to create an unassigned card.',
    )

    class Meta:
        model = RFIDCard
        fields = ['id_tag', 'card_number', 'customer', 'expiry_date', 'notes']
        widgets = {
            'id_tag': forms.TextInput(attrs={'class': 'form-control'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def save(self, commit=True, issued_by=None):
        card = super().save(commit=False)
        if card.customer:
            card.status = RFIDCard.Status.ACTIVE
            if issued_by:
                from django.utils import timezone
                card.issued_by = issued_by
                card.issued_at = timezone.now()
        else:
            card.status = RFIDCard.Status.UNASSIGNED
        if commit:
            card.save()
        return card


class RFIDCardUpdateForm(forms.ModelForm):
    class Meta:
        model = RFIDCard
        fields = ['card_number', 'status', 'expiry_date', 'notes']
        widgets = {
            'card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class RFIDCardAssignForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
