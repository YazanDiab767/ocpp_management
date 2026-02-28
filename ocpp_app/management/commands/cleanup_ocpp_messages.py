from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ocpp_app.models import OCPPMessage


class Command(BaseCommand):
    help = 'Delete OCPP messages older than N days to prevent database bloat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete messages older than this many days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report count without deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)

        qs = OCPPMessage.objects.filter(created_at__lt=cutoff)
        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(
                f'No OCPP messages older than {days} days.'
            ))
            return

        if dry_run:
            self.stdout.write(
                f'Would delete {count} OCPP message(s) older than {days} days.'
            )
        else:
            deleted, _ = qs.delete()
            self.stdout.write(self.style.SUCCESS(
                f'Deleted {deleted} OCPP message(s) older than {days} days.'
            ))
