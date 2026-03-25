from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from sessions.models import ChargingSession, MeterValue


@login_required
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


@login_required
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


@login_required
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
