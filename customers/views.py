from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import page_permission_required

from customers.forms import CustomerForm, WalletTopupForm
from customers.models import CarMake, Customer, WalletTransaction
from customers.services import CustomerService, WalletService


@page_permission_required('customers')
def customer_list(request):
    query = request.GET.get('q', '')
    make_id = request.GET.get('make', '')
    qs = Customer.objects.select_related('wallet', 'vehicle_make').all()
    if query:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone_number__icontains=query)
        )
    if make_id:
        qs = qs.filter(vehicle_make_id=make_id)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/customer_list.html', {
        'page_obj': page_obj,
        'query': query,
        'make_id': make_id,
        'car_makes': CarMake.objects.all(),
    })


@page_permission_required('customers')
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = CustomerService.create_customer(
                created_by=request.user,
                **form.cleaned_data,
            )
            messages.success(request, f'Customer {customer.full_name} created.')
            return redirect('customer-detail', pk=customer.pk)
    else:
        form = CustomerForm()
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'Create Customer',
    })


@page_permission_required('customers')
def customer_detail(request, pk):
    customer = get_object_or_404(
        Customer.objects.select_related('wallet', 'vehicle_make'),
        pk=pk,
    )
    rfid_cards = customer.rfid_cards.all()
    recent_transactions = WalletTransaction.objects.filter(
        wallet=customer.wallet,
    ).order_by('-created_at')[:10]
    return render(request, 'customers/customer_detail.html', {
        'customer': customer,
        'rfid_cards': rfid_cards,
        'recent_transactions': recent_transactions,
    })


@page_permission_required('customers')
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated.')
            return redirect('customer-detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'Edit Customer',
        'customer': customer,
    })


@page_permission_required('customers')
def wallet_topup(request, pk):
    customer = get_object_or_404(
        Customer.objects.select_related('wallet'),
        pk=pk,
    )
    if request.method == 'POST':
        form = WalletTopupForm(request.POST)
        if form.is_valid():
            WalletService.topup(
                wallet_id=customer.wallet.pk,
                amount=form.cleaned_data['amount'],
                created_by=request.user,
                description=form.cleaned_data.get('notes', ''),
                receipt_number=form.cleaned_data.get('receipt_number', ''),
            )
            messages.success(
                request,
                f'{form.cleaned_data["amount"]} ILS added to {customer.full_name}\'s wallet.',
            )
            return redirect('customer-detail', pk=customer.pk)
    else:
        form = WalletTopupForm()
    return render(request, 'customers/wallet_topup.html', {
        'form': form,
        'customer': customer,
    })


@page_permission_required('customers')
def wallet_ledger(request, pk):
    customer = get_object_or_404(
        Customer.objects.select_related('wallet'),
        pk=pk,
    )
    transactions = WalletTransaction.objects.filter(
        wallet=customer.wallet,
    ).select_related('created_by').order_by('-created_at')
    paginator = Paginator(transactions, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/wallet_ledger.html', {
        'customer': customer,
        'page_obj': page_obj,
    })
