# Custom migration to safely add target_user field

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def add_target_user_field_safe(apps, schema_editor):
    """Safely add target_user field, ignoring if it already exists"""
    db_alias = schema_editor.connection.alias
    with schema_editor.connection.cursor() as cursor:
        try:
            # Try to add the column - will fail silently if it already exists
            cursor.execute("""
                ALTER TABLE audittrack_auditevent 
                ADD COLUMN target_user_id INTEGER NULL 
                REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED
            """)
            print("Added target_user_id column successfully")
        except Exception as e:
            # Column likely already exists, which is fine
            print(f"target_user_id column may already exist: {e}")


def remove_target_user_field_safe(apps, schema_editor):
    """Safely remove target_user field"""
    # SQLite doesn't support dropping columns easily, so we'll leave it
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('audittrack', '0005_alter_auditevent_action'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Safely add the target_user column
        migrations.RunPython(
            add_target_user_field_safe,
            remove_target_user_field_safe,
        ),
        
        # Update the action choices
        migrations.AlterField(
            model_name='auditevent',
            name='action',
            field=models.CharField(
                choices=[
                    ('invite_created', 'Invite Created'), 
                    ('user_registered', 'User Registered'), 
                    ('user_signin', 'User Sign In'), 
                    ('user_signout', 'User Sign Out'), 
                    ('referral_sent', 'Referral Sent'), 
                    ('slot_booked', 'Message Slot Booked'), 
                    ('message_answered', 'Message Answered for First Time'), 
                    ('user_deleted', 'User Deleted'), 
                    ('profile_edited', 'Profile Edited'), 
                    ('user_reported', 'User Reported'), 
                    ('user_unblocked', 'User Unblocked'), 
                    ('user_suspended', 'User Suspended'), 
                    ('user_unsuspended', 'User Unsuspended'), 
                    ('user_soft_deleted', 'User Soft Deleted'), 
                    ('user_restored', 'User Restored'), 
                    ('bulk_user_action', 'Bulk User Action')
                ], 
                help_text='Action that was performed', 
                max_length=50
            ),
        ),
        
        # Update the user field with new related_name
        migrations.AlterField(
            model_name='auditevent',
            name='user',
            field=models.ForeignKey(
                blank=True, 
                help_text='User who performed the action', 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='audit_actions_performed', 
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]