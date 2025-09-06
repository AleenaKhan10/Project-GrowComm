from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from messaging.models import MessageType
from communities.models import Community


class Command(BaseCommand):
    help = 'Create initial data for GrwCommunity'

    def handle(self, *args, **options):
        # Create message types
        message_types = [
            {'name': 'Coffee Chat', 'description': 'Casual conversation over coffee', 'color_code': '#8B4513'},
            {'name': 'Mentorship', 'description': 'Career guidance and mentoring', 'color_code': '#4CAF50'},
            {'name': 'Networking', 'description': 'Professional networking opportunities', 'color_code': '#2196F3'},
            {'name': 'General', 'description': 'General conversation and questions', 'color_code': '#00ffff'},
        ]
        
        for mt_data in message_types:
            message_type, created = MessageType.objects.get_or_create(
                name=mt_data['name'],
                defaults={
                    'description': mt_data['description'],
                    'color_code': mt_data['color_code'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created message type: {message_type.name}')
                )
            else:
                self.stdout.write(f'Message type already exists: {message_type.name}')
        
        # Create default community
        community, created = Community.objects.get_or_create(
            name='GrwCommunity',
            defaults={
                'description': 'The main GrwCommunity where all members connect and share knowledge.',
                'is_active': True,
                'is_private': False,
                'created_by': User.objects.filter(is_superuser=True).first() or User.objects.first()
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created community: {community.name}')
            )
        else:
            self.stdout.write(f'Community already exists: {community.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up initial data!')
        )