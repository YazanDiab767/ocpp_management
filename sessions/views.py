import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import page_permission_required
from chargers.models import ChargePoint
from sessions.models import ChargingSession, MeterValue
from sessions.services import SessionService

logger = logging.getLogger('ocpp')


@page_permission_required('sessions')
def session_list(request):
    qs = ChargingSession.objects.select_related(
        'charge_point', 'connector', 'customer',
    ).all()

    status_filter = request.GET.get('status', '')
    cp_filter = request.GET.get('charge_point_id', '')
    search = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if cp_filter:
        qs = qs.filter(charge_point_id_str__icontains=cp_filter)
    if search:
        qs = qs.filter(
            Q(transaction_id__icontains=search)
            | Q(id_tag__icontains=search)
            | Q(customer__first_name__icontains=search)
            | Q(customer__last_name__icontains=search)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'sessions/session_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'cp_filter': cp_filter,
        'search': search,
        'status_choices': ChargingSession.Status.choices,
    })


@page_permission_required('sessions')
def session_detail(request, transaction_id):
    session = get_object_or_404(
        ChargingSession.objects.select_related(
            'charge_point', 'connector', 'rfid_card', 'customer', 'customer__wallet',
        ),
        transaction_id=transaction_id,
    )
    meter_values = session.meter_values.order_by('timestamp')

    return render(request, 'sessions/session_detail.html', {
        'session': session,
        'meter_values': meter_values,
    })


@page_permission_required('active_sessions')
def active_sessions(request):
    sessions = list(ChargingSession.objects.filter(
        status=ChargingSession.Status.ACTIVE,
    ).select_related('charge_point', 'connector', 'customer'))

    for s in sessions:
        latest_soc = s.meter_values.filter(measurand='SoC').order_by('-timestamp').first()
        latest_voltage = s.meter_values.filter(measurand='Voltage').order_by('-timestamp').first()
        latest_current = s.meter_values.filter(measurand='Current.Import').order_by('-timestamp').first()
        latest_power = s.meter_values.filter(measurand='Power.Active.Import').order_by('-timestamp').first()
        s.live_soc = latest_soc.value if latest_soc else None
        s.live_voltage = latest_voltage.value if latest_voltage else None
        s.live_current = latest_current.value if latest_current else None
        s.live_power = latest_power.value if latest_power else None

    return render(request, 'sessions/active_sessions.html', {
        'sessions': sessions,
    })


@page_permission_required('sessions')
@require_POST
def session_remote_stop(request, transaction_id):
    """Send RemoteStopTransaction to the charger via OCPP."""
    session = get_object_or_404(ChargingSession, transaction_id=transaction_id)

    if session.status != ChargingSession.Status.ACTIVE:
        messages.warning(request, f'Session #{transaction_id} is already {session.get_status_display()}.')
        return redirect('session-detail', transaction_id=transaction_id)

    try:
        cp = ChargePoint.objects.get(charge_point_id=session.charge_point_id_str)
        if cp.status != ChargePoint.Status.ONLINE:
            messages.error(
                request,
                f'Charger {session.charge_point_id_str} is offline. '
                f'Use "Force Close" instead to close the session on the server side.'
            )
            return redirect('session-detail', transaction_id=transaction_id)
    except ChargePoint.DoesNotExist:
        messages.error(request, 'Charger not found.')
        return redirect('session-detail', transaction_id=transaction_id)

    try:
        from ocpp_app.services import OCPPService
        OCPPService.send_remote_stop(session.charge_point_id_str, session.transaction_id)
        messages.success(request, f'RemoteStopTransaction sent to charger for session #{transaction_id}.')
    except Exception as e:
        messages.error(request, f'Failed to send RemoteStop: {e}')

    return redirect('session-detail', transaction_id=transaction_id)


@page_permission_required('sessions')
@require_POST
def session_force_close(request, transaction_id):
    """Force-close a stuck session on the server side. Works even if charger is offline."""
    session = get_object_or_404(ChargingSession, transaction_id=transaction_id)

    if session.status != ChargingSession.Status.ACTIVE:
        messages.warning(request, f'Session #{transaction_id} is already {session.get_status_display()}.')
        return redirect('session-detail', transaction_id=transaction_id)

    try:
        result = SessionService.force_close_session(transaction_id=transaction_id)
        if result:
            messages.success(
                request,
                f'Session #{transaction_id} force-closed. '
                f'Energy: {result.energy_delivered_kwh} kWh, Cost: {result.total_cost} ILS.'
            )
        else:
            messages.error(request, f'Session #{transaction_id} not found or already closed.')
    except Exception as e:
        messages.error(request, f'Failed to force-close session: {e}')

    return redirect('session-detail', transaction_id=transaction_id)


@page_permission_required('sessions')
@require_POST
def session_reset_charger(request, transaction_id):
    """Send a Soft or Hard Reset to the charger associated with this session."""
    session = get_object_or_404(ChargingSession, transaction_id=transaction_id)
    reset_type = request.POST.get('reset_type', 'Soft')

    try:
        cp = ChargePoint.objects.get(charge_point_id=session.charge_point_id_str)
        if cp.status != ChargePoint.Status.ONLINE:
            messages.error(request, f'Charger {session.charge_point_id_str} is offline. Cannot send reset.')
            return redirect('session-detail', transaction_id=transaction_id)
    except ChargePoint.DoesNotExist:
        messages.error(request, 'Charger not found.')
        return redirect('session-detail', transaction_id=transaction_id)

    try:
        from ocpp_app.services import OCPPService
        OCPPService.send_reset(session.charge_point_id_str, reset_type)
        messages.success(request, f'{reset_type} Reset sent to charger {session.charge_point_id_str}.')
    except Exception as e:
        messages.error(request, f'Failed to send reset: {e}')

    return redirect('session-detail', transaction_id=transaction_id)
