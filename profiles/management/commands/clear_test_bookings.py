from django.core.management.base import BaseCommand
from messaging.models import MessageSlotBooking, MessageType
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clear all message slot bookings for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear ALL bookings including expired ones',
        )
    
    def handle(self, *args, **options):
        if options['all']:
            bookings = MessageSlotBooking.objects.all()
            message = 'all bookings'
        else:
            bookings = MessageSlotBooking.objects.filter(expires_date__gt=timezone.now())
            message = 'active bookings'
        
        count = bookings.count()
        
        if count > 0:
            self.stdout.write(f'Found {count} {message}:')
            for booking in bookings:
                self.stdout.write(f'  - {booking.sender.username} -> {booking.receiver.username} ({booking.message_type.name})')
            
            bookings.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared {count} {message}')
            )
        else:
            self.stdout.write(f'No {message} found')