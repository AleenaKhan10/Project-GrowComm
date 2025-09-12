# Sync the model state with Django's migration system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    This migration tells Django that the target_user field already exists
    in the database, without trying to create it again.
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('audittrack', '0007_confirm_target_user_field'),
    ]

    operations = [
        # This tells Django that the field already exists in the database
        # but needs to be added to the model state
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # No database operations - field already exists
            ],
            state_operations=[
                # Tell Django's migration system about the field
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
                ),
            ],
        ),
    ]