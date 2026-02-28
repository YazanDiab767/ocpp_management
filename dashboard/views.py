from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.dateparse import parse_date

from dashboard.services import ReportService


@login_required
def dashboard_home(request):
    stats = ReportService.get_dashboard_stats()
    recent_sessions = ReportService.get_recent_sessions(limit=10)
    charger_summary = ReportService.get_charger_status_summary()

    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'recent_sessions': recent_sessions,
        'charger_summary': charger_summary,
    })


@login_required
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


@login_required
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
