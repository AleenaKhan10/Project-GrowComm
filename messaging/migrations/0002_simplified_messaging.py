# Generated manually for messaging system simplification

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0001_initial'),
    ]

    operations = [
        # 1. Add new fields to Message model
        migrations.AddField(
            model_name='message',
            name='receiver',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_messages_new',
                to='auth.user'
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='timestamp',
            field=models.DateTimeField(
                default=django.utils.timezone.now
            ),
        ),
        
        # 2. Data migration to copy recipient to receiver and created_date to timestamp
        migrations.RunSQL(
            sql="""
            UPDATE messaging_message 
            SET receiver_id = recipient_id,
                timestamp = created_date
            WHERE recipient_id IS NOT NULL
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        
        # 3. Make conversation and message_type nullable
        migrations.AlterField(
            model_name='message',
            name='conversation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='messages',
                to='messaging.conversation'
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='message_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='messages',
                to='messaging.messagetype'
            ),
        ),
        
        # 4. Remove NOT NULL constraint from receiver
        migrations.AlterField(
            model_name='message',
            name='receiver',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_messages_new',
                to='auth.user'
            ),
        ),
        
        # 5. Add indexes for performance
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['sender', 'receiver', '-timestamp'], name='messaging_m_sender__e8c4d7_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['receiver', 'is_read', '-timestamp'], name='messaging_m_receive_1e3a9f_idx'),
        ),
        
        # 6. Change Meta ordering
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['-timestamp']},
        ),
        
        # 7. Remove old fields (commented out for now to maintain backward compatibility)
        # migrations.RemoveField(
        #     model_name='message',
        #     name='recipient',
        # ),
        # migrations.RemoveField(
        #     model_name='message',
        #     name='created_date',
        # ),
    ]