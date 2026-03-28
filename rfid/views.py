from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from rfid.forms import RFIDCardCreateForm, RFIDCardUpdateForm, RFIDCardAssignForm
from rfid.models import RFIDCard, RFIDTapLog
from rfid.services import RFIDService


@login_required
def tap_log(request):
    qs = RFIDTapLog.objects.select_related('rfid_card').all()
    result_filter = request.GET.get('result')
    if result_filter:
        qs = qs.filter(result=result_filter)
    query = request.GET.get('q', '')
    if query:
        from django.db.models import Q
        qs = qs.filter(
            Q(id_tag__icontains=query)
            | Q(charge_point_id__icontains=query)
            | Q(customer_name__icontains=query)
        )
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'rfid/tap_log.html', {
        'page_obj': page_obj,
        'query': query,
        'result_filter': result_filter,
        'result_choices': RFIDTapLog.Result.choices,
    })


@login_required
def card_list(request):
    qs = RFIDCard.objects.select_related('customer').all()
    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    query = request.GET.get('q', '')
    if query:
        from django.db.models import Q
        qs = qs.filter(
            Q(id_tag__icontains=query)
            | Q(card_number__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'rfid/card_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'status_choices': RFIDCard.Status.choices,
    })


@login_required
def card_create(request):
    initial = {}
    customer_id = request.GET.get('customer')
    if customer_id:
        initial['customer'] = customer_id
    if request.method == 'POST':
        form = RFIDCardCreateForm(request.POST)
        if form.is_valid():
            card = form.save(issued_by=request.user)
            messages.success(request, f'RFID card {card.card_number} created.')
            return redirect('card-detail', pk=card.pk)
    else:
        form = RFIDCardCreateForm(initial=initial)
    return render(request, 'rfid/card_form.html', {
        'form': form,
        'title': 'Register RFID Card',
    })


@login_required
def card_detail(request, pk):
    card = get_object_or_404(
        RFIDCard.objects.select_related('customer', 'customer__wallet', 'issued_by'),
        pk=pk,
    )
    return render(request, 'rfid/card_detail.html', {'card': card})


@login_required
def card_update(request, pk):
    card = get_object_or_404(RFIDCard, pk=pk)
    if request.method == 'POST':
        form = RFIDCardUpdateForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, 'Card updated.')
            return redirect('card-detail', pk=card.pk)
    else:
        form = RFIDCardUpdateForm(instance=card)
    return render(request, 'rfid/card_form.html', {
        'form': form,
        'title': 'Edit RFID Card',
        'card': card,
    })


@login_required
def card_assign(request, pk):
    card = get_object_or_404(RFIDCard, pk=pk)
    if request.method == 'POST':
        form = RFIDCardAssignForm(request.POST)
        if form.is_valid():
            RFIDService.assign_to_customer(
                card_id=card.pk,
                customer_id=form.cleaned_data['customer'].pk,
                issued_by=request.user,
            )
            messages.success(request, f'Card assigned to {form.cleaned_data["customer"]}.')
            return redirect('card-detail', pk=card.pk)
    else:
        form = RFIDCardAssignForm()
    return render(request, 'rfid/card_assign.html', {
        'form': form,
        'card': card,
    })


@login_required
def card_block(request, pk):
    card = get_object_or_404(RFIDCard, pk=pk)
    if request.method == 'POST':
        RFIDService.block_card(card.pk)
        messages.success(request, f'Card {card.card_number} blocked.')
    return redirect('card-detail', pk=card.pk)


@login_required
def card_unassign(request, pk):
    card = get_object_or_404(RFIDCard, pk=pk)
    if request.method == 'POST':
        RFIDService.unassign_card(card.pk)
        messages.success(request, f'Card {card.card_number} unassigned.')
    return redirect('card-detail', pk=card.pk)
