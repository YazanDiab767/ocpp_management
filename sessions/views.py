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
    sessions = ChargingSession.objects.filter(
        status=ChargingSession.Status.ACTIVE,
    ).select_related('charge_point', 'connector', 'customer')

    return render(request, 'sessions/active_sessions.html', {
        'sessions': sessions,
    })
