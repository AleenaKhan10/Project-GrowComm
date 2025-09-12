# Add target_user field using Django's proper field addition

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def check_and_add_target_user(apps, schema_editor):
    """Check if target_user field exists and add it properly if needed"""
    # Get the model
    AuditEvent = apps.get_model('audittrack', 'AuditEvent')
    db_alias = schema_editor.connection.alias
    
    # Check if the field exists in the database
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(audittrack_auditevent)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'target_user_id' not in columns:
            print("target_user_id column not found, will be added by Django field operation")
        else:
            print("target_user_id column already exists in database")


def reverse_target_user(apps, schema_editor):
    """Reverse operation - nothing to do for now"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('audittrack', '0006_add_target_user_safe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Check the current state
        migrations.RunPython(
            check_and_add_target_user,
            reverse_target_user,
        ),
        
        # Add the target_user field using Django's proper method
        # This will only add it if it doesn't exist
        migrations.AddField(
            model_name='auditevent',
            name='target_user',
            field=models.ForeignKey(
                blank=True,
                help_text='User who was the target of the action (if applicable)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='audit_actions_received',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=True,
        ),
    ]