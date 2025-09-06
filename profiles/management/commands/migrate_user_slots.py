from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from messaging.models import UserMessageSettings


class Command(BaseCommand):
    help = 'Create UserMessageSettings for existing users who dont have them'
    
    def handle(self, *args, **options):
        users_without_settings = User.objects.filter(message_settings__isnull=True)
        created_count = 0
        
        for user in users_without_settings:
            settings, created = UserMessageSettings.objects.get_or_create(user=user)
            if created:
                created_count += 1
                self.stdout.write(f'Created message settings for {user.username}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} UserMessageSettings records'
            )
        )