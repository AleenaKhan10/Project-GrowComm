from django.core.management.base import BaseCommand
from messaging.models import MessageType


class Command(BaseCommand):
    help = 'Create default message types for the slot system'

    def handle(self, *args, **options):
        message_types = [
            {
                'name': 'Coffee Chat',
                'description': 'Informal conversation over coffee or a casual meeting',
                'color_code': '#8B4513'  # Brown
            },
            {
                'name': 'Mentorship',
                'description': 'Seeking guidance, advice, or career mentoring',
                'color_code': '#4A90E2'  # Blue
            },
            {
                'name': 'Networking',
                'description': 'Professional networking and connection building',
                'color_code': '#50C878'  # Green
            },
            {
                'name': 'General',
                'description': 'General conversation and networking',
                'color_code': '#9B59B6'  # Purple
            },
        ]

        created_count = 0
        for msg_type_data in message_types:
            msg_type, created = MessageType.objects.get_or_create(
                name=msg_type_data['name'],
                defaults={
                    'description': msg_type_data['description'],
                    'color_code': msg_type_data['color_code'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created message type: {msg_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Message type already exists: {msg_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} message types')
        )