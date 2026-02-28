from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone

from chargers.models import ChargePoint
from customers.models import Customer
from sessions.models import ChargingSession


class ReportService:

    @staticmethod
    def get_dashboard_stats():
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_customers = Customer.objects.filter(is_active=True).count()
        chargers_online = ChargePoint.objects.filter(status=ChargePoint.Status.ONLINE).count()
        chargers_total = ChargePoint.objects.count()
        active_sessions = ChargingSession.objects.filter(
            status=ChargingSession.Status.ACTIVE,
        ).count()

        today_agg = ChargingSession.objects.filter(
            status=ChargingSession.Status.COMPLETED,
            stopped_at__gte=today_start,
        ).aggregate(
            revenue=Sum('total_cost'),
            energy=Sum('energy_delivered_kwh'),
            count=Count('id'),
        )

        return {
            'total_customers': total_customers,
            'chargers_online': chargers_online,
            'chargers_total': chargers_total,
            'active_sessions': active_sessions,
            'today_revenue': today_agg['revenue'] or Decimal('0.00'),
            'today_energy': today_agg['energy'] or Decimal('0.000'),
            'today_sessions': today_agg['count'],
        }

    @staticmethod
    def get_recent_sessions(limit=10):
        return ChargingSession.objects.select_related(
            'charge_point', 'customer',
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_charger_status_summary():
        return ChargePoint.objects.values('status').annotate(
            count=Count('id'),
        ).order_by('status')

    @staticmethod
    def get_session_report(date_from=None, date_to=None, charge_point_id=None):
        qs = ChargingSession.objects.select_related(
            'charge_point', 'customer',
        ).filter(status=ChargingSession.Status.COMPLETED)

        if date_from:
            qs = qs.filter(started_at__gte=date_from)
        if date_to:
            qs = qs.filter(started_at__lte=date_to)
        if charge_point_id:
            qs = qs.filter(charge_point_id_str=charge_point_id)

        sessions = qs.order_by('-started_at')

        totals = qs.aggregate(
            total_energy=Sum('energy_delivered_kwh'),
            total_revenue=Sum('total_cost'),
            session_count=Count('id'),
        )

        return sessions, {
            'total_energy': totals['total_energy'] or Decimal('0.000'),
            'total_revenue': totals['total_revenue'] or Decimal('0.00'),
            'session_count': totals['session_count'],
        }

    @staticmethod
    def get_revenue_report(date_from=None, date_to=None):
        qs = ChargingSession.objects.filter(
            status=ChargingSession.Status.COMPLETED,
        )

        if date_from:
            qs = qs.filter(stopped_at__gte=date_from)
        if date_to:
            qs = qs.filter(stopped_at__lte=date_to)

        totals = qs.aggregate(
            total_revenue=Sum('total_cost'),
            total_energy=Sum('energy_delivered_kwh'),
            session_count=Count('id'),
        )

        # Per-charger breakdown
        per_charger = qs.values(
            'charge_point_id_str',
        ).annotate(
            revenue=Sum('total_cost'),
            energy=Sum('energy_delivered_kwh'),
            sessions=Count('id'),
        ).order_by('-revenue')

        return {
            'total_revenue': totals['total_revenue'] or Decimal('0.00'),
            'total_energy': totals['total_energy'] or Decimal('0.000'),
            'session_count': totals['session_count'],
            'per_charger': per_charger,
        }
