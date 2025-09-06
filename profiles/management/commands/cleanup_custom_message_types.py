from django.core.management.base import BaseCommand
from messaging.models import MessageType


class Command(BaseCommand):
    help = 'Remove old custom MessageType objects that were incorrectly created globally'
    
    def handle(self, *args, **options):
        # Delete message types that start with "Custom:" which were created by mistake
        custom_types = MessageType.objects.filter(description__startswith='Custom:')
        count = custom_types.count()
        
        if count > 0:
            self.stdout.write(f'Found {count} incorrect custom message types:')
            for msg_type in custom_types:
                self.stdout.write(f'  - {msg_type.name}: {msg_type.description}')
            
            # Delete them
            custom_types.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count} incorrect custom message types')
            )
        else:
            self.stdout.write('No incorrect custom message types found')