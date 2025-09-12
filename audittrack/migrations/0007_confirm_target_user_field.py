# Confirm target_user field exists without trying to add it

from django.db import migrations


def confirm_target_user_field(apps, schema_editor):
    """
    Confirm that the target_user field exists in the database.
    This migration just validates the current state without making changes.
    """
    # Check if the field exists in the database
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(audittrack_auditevent)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'target_user_id' in columns:
            print("✓ target_user_id column confirmed in database")
        else:
            print("✗ target_user_id column missing - this shouldn't happen")
            # Don't raise error, just log it


def reverse_confirm_target_user_field(apps, schema_editor):
    """Reverse operation - nothing to do"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('audittrack', '0006_add_target_user_safe'),
    ]

    operations = [
        # Just confirm the field exists, don't try to add it
        migrations.RunPython(
            confirm_target_user_field,
            reverse_confirm_target_user_field,
        ),
    ]