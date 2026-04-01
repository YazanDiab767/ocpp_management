from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from accounts.decorators import page_permission_required
from customers.models import WalletTransaction
from dashboard.services import ReportService

User = get_user_model()


@login_required
def dashboard_home(request):
    # Dashboard is always accessible to logged-in users, but the template
    # filters widgets based on allowed_pages from the context processor
    stats = ReportService.get_dashboard_stats()
    recent_sessions = ReportService.get_recent_sessions(limit=10)
    charger_summary = ReportService.get_charger_status_summary()

    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'recent_sessions': recent_sessions,
        'charger_summary': charger_summary,
    })


@page_permission_required('session_report')
def report_sessions(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    cp_id = request.GET.get('charge_point_id', '')

    date_from_parsed = parse_date(date_from) if date_from else None
    date_to_parsed = parse_date(date_to) if date_to else None

    sessions, totals = ReportService.get_session_report(
        date_from=date_from_parsed,
        date_to=date_to_parsed,
        charge_point_id=cp_id or None,
    )

    paginator = Paginator(sessions, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/report_sessions.html', {
        'page_obj': page_obj,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'cp_id': cp_id,
    })


@page_permission_required('revenue_report')
def report_revenue(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    date_from_parsed = parse_date(date_from) if date_from else None
    date_to_parsed = parse_date(date_to) if date_to else None

    report = ReportService.get_revenue_report(
        date_from=date_from_parsed,
        date_to=date_to_parsed,
    )

    return render(request, 'dashboard/report_revenue.html', {
        'report': report,
        'date_from': date_from,
        'date_to': date_to,
    })


@page_permission_required('topup_report')
def report_topups(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    customer_q = request.GET.get('customer', '')
    created_by = request.GET.get('created_by', '')

    qs = WalletTransaction.objects.filter(
        transaction_type=WalletTransaction.TransactionType.TOPUP,
    ).select_related('wallet__customer', 'created_by').order_by('-created_at')

    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            qs = qs.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            qs = qs.filter(created_at__date__lte=parsed)
    if customer_q:
        qs = qs.filter(
            Q(wallet__customer__first_name__icontains=customer_q)
            | Q(wallet__customer__last_name__icontains=customer_q)
            | Q(wallet__customer__phone_number__icontains=customer_q)
        )
    if created_by:
        qs = qs.filter(created_by_id=created_by)

    totals = qs.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id'),
    )

    staff_users = User.objects.filter(is_active=True).order_by('full_name')

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/report_topups.html', {
        'page_obj': page_obj,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'customer_q': customer_q,
        'created_by': created_by,
        'staff_users': staff_users,
    })
