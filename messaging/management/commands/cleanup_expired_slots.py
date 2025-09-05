from django.core.management.base import BaseCommand
from django.utils import timezone
from messaging.models import MessageSlotBooking


class Command(BaseCommand):
    help = 'Clean up expired message slot bookings (older than 3 days)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            expired_count = MessageSlotBooking.objects.filter(
                expires_date__lt=timezone.now()
            ).count()
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {expired_count} expired slot bookings')
            )
        else:
            expired_count = MessageSlotBooking.cleanup_expired_bookings()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {expired_count} expired slot bookings')
            )