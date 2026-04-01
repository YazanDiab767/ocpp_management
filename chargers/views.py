from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import page_permission_required
from django.views.decorators.http import require_POST

from chargers.forms import ChargePointForm
from chargers.models import ChargePoint, Connector
from ocpp_app.models import OCPPMessage
from ocpp_app.services import OCPPService
from rfid.models import RFIDCard
from sessions.models import ChargingSession


@page_permission_required('chargers')
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


@page_permission_required('chargers')
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


@page_permission_required('chargers')
def charger_detail(request, pk):
    cp = get_object_or_404(ChargePoint.objects.prefetch_related('connectors'), pk=pk)
    recent_messages = OCPPMessage.objects.filter(
        charge_point_id=cp.charge_point_id,
    ).order_by('-created_at')[:20]
    rfid_cards = RFIDCard.objects.filter(status='active').select_related('customer')
    active_sessions = list(ChargingSession.objects.filter(
        charge_point_id_str=cp.charge_point_id,
        status=ChargingSession.Status.ACTIVE,
    ).select_related('customer'))
    for s in active_sessions:
        latest_soc = s.meter_values.filter(measurand='SoC').order_by('-timestamp').first()
        latest_voltage = s.meter_values.filter(measurand='Voltage').order_by('-timestamp').first()
        s.live_soc = latest_soc.value if latest_soc else None
        s.live_voltage = latest_voltage.value if latest_voltage else None
    return render(request, 'chargers/charger_detail.html', {
        'charger': cp,
        'connectors': cp.connectors.all(),
        'recent_messages': recent_messages,
        'rfid_cards': rfid_cards,
        'active_sessions': active_sessions,
    })


@page_permission_required('chargers')
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


@page_permission_required('chargers')
@require_POST
def charger_command(request, pk):
    cp = get_object_or_404(ChargePoint, pk=pk)
    command = request.POST.get('command')

    if cp.status != ChargePoint.Status.ONLINE:
        messages.error(request, 'Charger is offline. Cannot send commands.')
        return redirect('charger-detail', pk=cp.pk)

    try:
        if command == 'reset_soft':
            OCPPService.send_reset(cp.charge_point_id, 'Soft')
            messages.success(request, 'Soft Reset command sent.')
        elif command == 'reset_hard':
            OCPPService.send_reset(cp.charge_point_id, 'Hard')
            messages.warning(request, 'Hard Reset command sent.')
        elif command == 'trigger_heartbeat':
            OCPPService.send_trigger_message(cp.charge_point_id, 'Heartbeat')
            messages.success(request, 'TriggerMessage (Heartbeat) sent.')
        elif command == 'trigger_status':
            OCPPService.send_trigger_message(cp.charge_point_id, 'StatusNotification')
            messages.success(request, 'TriggerMessage (StatusNotification) sent.')
        elif command == 'trigger_meter':
            OCPPService.send_trigger_message(cp.charge_point_id, 'MeterValues')
            messages.success(request, 'TriggerMessage (MeterValues) sent.')
        elif command == 'trigger_boot':
            OCPPService.send_trigger_message(cp.charge_point_id, 'BootNotification')
            messages.success(request, 'TriggerMessage (BootNotification) sent.')
        elif command == 'get_config':
            OCPPService.send_get_configuration(cp.charge_point_id)
            messages.success(request, 'GetConfiguration sent. Check the OCPP Log for the response.')
        elif command == 'remote_start':
            id_tag = request.POST.get('id_tag', '')
            connector_id = int(request.POST.get('connector_id', 1))
            if not id_tag:
                messages.error(request, 'Please select an RFID card.')
            else:
                OCPPService.send_remote_start(cp.charge_point_id, connector_id, id_tag)
                messages.success(request, f'RemoteStartTransaction sent (idTag={id_tag}, connector={connector_id}).')
        elif command == 'remote_stop':
            transaction_id = request.POST.get('transaction_id', '')
            if not transaction_id:
                messages.error(request, 'No active session to stop.')
            else:
                OCPPService.send_remote_stop(cp.charge_point_id, int(transaction_id))
                messages.success(request, f'RemoteStopTransaction sent (txn={transaction_id}).')
        elif command == 'change_config':
            key = request.POST.get('config_key', '').strip()
            value = request.POST.get('config_value', '').strip()
            if not key or not value:
                messages.error(request, 'Both key and value are required.')
            else:
                OCPPService.send_change_configuration(cp.charge_point_id, key, value)
                messages.success(request, f'ChangeConfiguration sent: {key} = {value}. Check OCPP Log for the response.')
        elif command == 'change_availability':
            connector_id = int(request.POST.get('connector_id', 0))
            availability_type = request.POST.get('availability_type', 'Operative')
            if availability_type not in ('Operative', 'Inoperative'):
                messages.error(request, 'Invalid availability type.')
            else:
                OCPPService.send_change_availability(cp.charge_point_id, connector_id, availability_type)
                label = 'Enabled' if availability_type == 'Operative' else 'Disabled'
                target = f'Connector {connector_id}' if connector_id > 0 else 'All connectors'
                messages.success(request, f'ChangeAvailability sent: {target} → {label}.')
        else:
            messages.error(request, f'Unknown command: {command}')
    except Exception as e:
        messages.error(request, f'Failed to send command: {e}')

    return redirect('charger-detail', pk=cp.pk)


@page_permission_required('chargers')
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
