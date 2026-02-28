from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from chargers.forms import ChargePointForm
from chargers.models import ChargePoint, Connector
from ocpp_app.models import OCPPMessage


@login_required
def charger_list(request):
    qs = ChargePoint.objects.prefetch_related('connectors').all().order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'chargers/charger_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': ChargePoint.Status.choices,
    })


@login_required
def charger_create(request):
    if request.method == 'POST':
        form = ChargePointForm(request.POST)
        if form.is_valid():
            cp = form.save()
            messages.success(request, f'Charger "{cp.name}" registered.')
            return redirect('charger-detail', pk=cp.pk)
    else:
        form = ChargePointForm()
    return render(request, 'chargers/charger_form.html', {
        'form': form,
        'title': 'Register Charger',
    })


@login_required
def charger_detail(request, pk):
    cp = get_object_or_404(ChargePoint.objects.prefetch_related('connectors'), pk=pk)
    recent_messages = OCPPMessage.objects.filter(
        charge_point_id=cp.charge_point_id,
    ).order_by('-created_at')[:20]
    return render(request, 'chargers/charger_detail.html', {
        'charger': cp,
        'connectors': cp.connectors.all(),
        'recent_messages': recent_messages,
    })


@login_required
def charger_update(request, pk):
    cp = get_object_or_404(ChargePoint, pk=pk)
    if request.method == 'POST':
        form = ChargePointForm(request.POST, instance=cp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Charger updated.')
            return redirect('charger-detail', pk=cp.pk)
    else:
        form = ChargePointForm(instance=cp)
    return render(request, 'chargers/charger_form.html', {
        'form': form,
        'title': 'Edit Charger',
        'charger': cp,
    })


@login_required
def charger_messages(request, pk):
    cp = get_object_or_404(ChargePoint, pk=pk)
    msgs = OCPPMessage.objects.filter(
        charge_point_id=cp.charge_point_id,
    ).order_by('-created_at')
    paginator = Paginator(msgs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'chargers/charger_messages.html', {
        'charger': cp,
        'page_obj': page_obj,
    })
