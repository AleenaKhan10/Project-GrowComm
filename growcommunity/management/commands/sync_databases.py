from django.core.management.base import BaseCommand
from django.db import connections
from growcommunity.dual_db_sync import sync_existing_data, test_postgresql_connection


class Command(BaseCommand):
    help = 'Manage dual database synchronization between SQLite and PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test PostgreSQL database connection',
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sync all existing SQLite data to PostgreSQL',
        )
        parser.add_argument(
            '--migrate-postgresql',
            action='store_true',
            help='Run migrations on PostgreSQL database',
        )

    def handle(self, *args, **options):
        if options['test_connection']:
            self.stdout.write('Testing PostgreSQL connection...')
            if test_postgresql_connection():
                self.stdout.write(
                    self.style.SUCCESS('PostgreSQL connection successful!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('PostgreSQL connection failed!')
                )
        
        elif options['migrate_postgresql']:
            self.stdout.write('Running migrations on PostgreSQL database...')
            from django.core.management import call_command
            try:
                call_command('migrate', database='postgresql', verbosity=2)
                self.stdout.write(
                    self.style.SUCCESS('PostgreSQL migrations completed!')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Migration failed: {e}')
                )
        
        elif options['sync_all']:
            self.stdout.write('Starting full data synchronization...')
            try:
                sync_existing_data()
                self.stdout.write(
                    self.style.SUCCESS('Data synchronization completed!')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Synchronization failed: {e}')
                )
        
        else:
            self.stdout.write('Available options:')
            self.stdout.write('  --test-connection     Test PostgreSQL connection')
            self.stdout.write('  --migrate-postgresql  Run migrations on PostgreSQL')
            self.stdout.write('  --sync-all           Sync all data to PostgreSQL')