from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from sessions.models import ChargingSession


class Command(BaseCommand):
    help = 'Find and optionally close stale active sessions (no updates for N hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=6,
            help='Consider sessions stale after this many hours of inactivity (default: 6)',
        )
        parser.add_argument(
            '--close',
            action='store_true',
            help='Actually close stale sessions (default: dry run / report only)',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        close = options['close']
        cutoff = timezone.now() - timedelta(hours=hours)

        stale = ChargingSession.objects.filter(
            status=ChargingSession.Status.ACTIVE,
            updated_at__lt=cutoff,
        ).select_related('charge_point', 'customer')

        count = stale.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No stale sessions found.'))
            return

        self.stdout.write(f'Found {count} stale session(s) (inactive > {hours}h):')
        for session in stale:
            self.stdout.write(
                f'  txn={session.transaction_id} '
                f'cp={session.charge_point_id_str} '
                f'started={session.started_at} '
                f'last_update={session.updated_at}'
            )

        if close:
            now = timezone.now()
            updated = stale.update(
                status=ChargingSession.Status.COMPLETED,
                stop_reason='StaleSessionCleanup',
                stopped_at=now,
            )
            self.stdout.write(self.style.WARNING(f'Closed {updated} stale session(s).'))
        else:
            self.stdout.write(self.style.NOTICE(
                'Dry run. Use --close to actually close these sessions.'
            ))
