from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required
from billing.forms import BillingPolicyForm, TariffForm
from billing.models import BillingPolicy, Tariff
from billing.services import TariffService


@admin_required
def tariff_list(request):
    tariffs = Tariff.objects.all()
    return render(request, 'billing/tariff_list.html', {'tariffs': tariffs})


@admin_required
def tariff_create(request):
    if request.method == 'POST':
        form = TariffForm(request.POST)
        if form.is_valid():
            activate = form.cleaned_data.pop('activate', False)
            tariff = TariffService.create_tariff(
                activate=activate,
                **form.cleaned_data,
            )
            messages.success(request, f'Tariff "{tariff.name}" created.')
            return redirect('tariff-list')
    else:
        form = TariffForm()
    return render(request, 'billing/tariff_form.html', {'form': form, 'title': 'Create Tariff'})


@admin_required
def tariff_update(request, pk):
    tariff = get_object_or_404(Tariff, pk=pk)
    if request.method == 'POST':
        form = TariffForm(request.POST, instance=tariff)
        if form.is_valid():
            activate = form.cleaned_data.pop('activate', False)
            tariff = form.save(commit=False)
            if activate:
                TariffService.activate_tariff(tariff.pk)
                tariff.is_active = True
            tariff.save()
            messages.success(request, f'Tariff "{tariff.name}" updated.')
            return redirect('tariff-list')
    else:
        form = TariffForm(instance=tariff, initial={'activate': tariff.is_active})
    return render(request, 'billing/tariff_form.html', {'form': form, 'title': 'Edit Tariff'})


@admin_required
def tariff_activate(request, pk):
    if request.method == 'POST':
        TariffService.activate_tariff(pk)
        messages.success(request, 'Tariff activated.')
    return redirect('tariff-list')


@admin_required
def billing_policy(request):
    policy = BillingPolicy.load()
    if request.method == 'POST':
        form = BillingPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Billing policy updated.')
            return redirect('billing-policy')
    else:
        form = BillingPolicyForm(instance=policy)
    return render(request, 'billing/billing_policy.html', {'form': form, 'policy': policy})
