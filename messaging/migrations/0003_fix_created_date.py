# Migration to fix the created_date field issue

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_simplified_messaging'),
    ]

    operations = [
        # Make created_date nullable temporarily
        migrations.AlterField(
            model_name='message',
            name='created_date',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                null=True,
                blank=True
            ),
        ),
        
        # Make recipient nullable temporarily  
        migrations.AlterField(
            model_name='message',
            name='recipient',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name='received_messages_old',
                to='auth.user'
            ),
        ),
    ]