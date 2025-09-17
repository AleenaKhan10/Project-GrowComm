"""
Dual Database Synchronization using Django Signals
This module ensures all data modifications are replicated to both databases.
"""

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.db import connections, transaction
from django.apps import apps
import logging
import threading

logger = logging.getLogger(__name__)

# Thread-local storage to prevent infinite recursion
_thread_locals = threading.local()


def is_sync_enabled():
    """Check if sync is enabled for current thread."""
    return getattr(_thread_locals, 'sync_enabled', True)


def disable_sync():
    """Temporarily disable sync for current thread."""
    _thread_locals.sync_enabled = False


def enable_sync():
    """Re-enable sync for current thread."""
    _thread_locals.sync_enabled = True


class DualDatabaseSync:
    """
    Handles synchronization between SQLite and PostgreSQL databases.
    """
    
    @staticmethod
    def sync_save(sender, instance, created, **kwargs):
        """
        Sync save operations to PostgreSQL database.
        """
        if not is_sync_enabled():
            return
            
        # Skip if this is already a PostgreSQL operation
        if hasattr(instance._state, 'db') and instance._state.db == 'postgresql':
            return
        
        try:
            # Temporarily disable sync to prevent recursion
            disable_sync()
            
            # Test connection before attempting save
            from django.db import connections
            pg_conn = connections['postgresql']
            
            # Quick connection test with short timeout
            with pg_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Save to PostgreSQL
            instance.save(using='postgresql', force_insert=created)
            
            logger.debug(f"Synced {sender.__name__} (id={instance.pk}) to PostgreSQL")
        except Exception as e:
            logger.warning(f"Failed to sync {sender.__name__} to PostgreSQL: {e}")
            # Don't raise the exception - we want the primary operation to succeed
            # This allows the app to continue working even if PostgreSQL is unavailable
        finally:
            enable_sync()
    
    @staticmethod
    def sync_delete(sender, instance, **kwargs):
        """
        Sync delete operations to PostgreSQL database.
        """
        if not is_sync_enabled():
            return
            
        # Skip if this is already a PostgreSQL operation
        if instance._state.db == 'postgresql':
            return
        
        try:
            # Temporarily disable sync to prevent recursion
            disable_sync()
            
            # Try to get and delete from PostgreSQL
            if instance.pk:
                sender.objects.using('postgresql').filter(pk=instance.pk).delete()
                logger.debug(f"Synced delete of {sender.__name__} (id={instance.pk}) to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to sync delete {sender.__name__} to PostgreSQL: {e}")
        finally:
            enable_sync()
    
    @staticmethod
    def sync_m2m(sender, instance, action, pk_set, model, **kwargs):
        """
        Sync many-to-many changes to PostgreSQL database.
        """
        if not is_sync_enabled() or not pk_set:
            return
            
        # Skip if this is already a PostgreSQL operation
        if instance._state.db == 'postgresql':
            return
        
        try:
            disable_sync()
            
            # Get the field name from the sender (through table)
            field_name = None
            for field in instance._meta.get_fields():
                if hasattr(field, 'through') and field.through == sender:
                    field_name = field.name
                    break
            
            if not field_name:
                return
            
            # Get the PostgreSQL instance
            pg_instance = instance.__class__.objects.using('postgresql').get(pk=instance.pk)
            m2m_field = getattr(pg_instance, field_name)
            
            if action == "post_add":
                m2m_field.add(*pk_set)
            elif action == "post_remove":
                m2m_field.remove(*pk_set)
            elif action == "post_clear":
                m2m_field.clear()
            
            logger.debug(f"Synced M2M {action} for {instance.__class__.__name__} to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to sync M2M change to PostgreSQL: {e}")
        finally:
            enable_sync()


def connect_signals():
    """
    Connect signals for all models to enable dual database sync.
    """
    sync = DualDatabaseSync()
    
    # Connect signals for all models
    for model in apps.get_models():
        # Skip Django's internal models
        if model._meta.app_label in ['contenttypes', 'sessions', 'admin', 'auth']:
            continue
            
        # Connect save and delete signals
        post_save.connect(sync.sync_save, sender=model, weak=False)
        post_delete.connect(sync.sync_delete, sender=model, weak=False)
        
        # Connect M2M signals
        for field in model._meta.get_fields():
            if hasattr(field, 'through'):
                m2m_changed.connect(sync.sync_m2m, sender=field.through, weak=False)
    
    logger.info("Dual database sync signals connected")


def sync_existing_data():
    """
    One-time sync of all existing SQLite data to PostgreSQL.
    Call this function to initially populate PostgreSQL with existing data.
    """
    from django.db import connection
    
    logger.info("Starting initial data sync from SQLite to PostgreSQL...")
    
    disable_sync()  # Disable auto-sync during bulk operation
    
    try:
        with transaction.atomic(using='postgresql'):
            for model in apps.get_models():
                # Skip Django's internal models
                if model._meta.app_label in ['contenttypes', 'sessions']:
                    continue
                
                model_name = f"{model._meta.app_label}.{model.__name__}"
                
                try:
                    # Get all objects from SQLite
                    objects = model.objects.using('default').all()
                    count = objects.count()
                    
                    if count > 0:
                        # Delete existing data in PostgreSQL for this model
                        model.objects.using('postgresql').all().delete()
                        
                        # Bulk create in PostgreSQL
                        # We need to handle this in batches for large datasets
                        batch_size = 1000
                        for i in range(0, count, batch_size):
                            batch = list(objects[i:i+batch_size])
                            
                            # Clear the state to indicate these are new objects for PostgreSQL
                            for obj in batch:
                                obj._state.db = 'postgresql'
                                obj._state.adding = True
                            
                            model.objects.using('postgresql').bulk_create(batch, ignore_conflicts=True)
                        
                        logger.info(f"Synced {count} {model_name} records to PostgreSQL")
                    
                except Exception as e:
                    logger.error(f"Failed to sync {model_name}: {e}")
                    # Continue with other models
                    
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")
        raise
    finally:
        enable_sync()
    
    logger.info("Initial data sync completed")


# Management command support
def handle_dual_db_command(command, *args, **options):
    """
    Handle management commands for dual database operations.
    """
    if command == 'sync_to_postgresql':
        sync_existing_data()
    elif command == 'test_connection':
        test_postgresql_connection()


def test_postgresql_connection():
    """
    Test the PostgreSQL database connection.
    """
    from django.db import connections
    
    try:
        conn = connections['postgresql']
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            logger.info(f"PostgreSQL connection successful. Version: {version}")
            print(f"[SUCCESS] PostgreSQL connection successful")
            print(f"  Database: grwcomm")
            print(f"  Host: grwcomm.c2z0ui48odxp.us-east-1.rds.amazonaws.com")
            print(f"  Version: {version}")
            return True
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        print(f"[FAILED] PostgreSQL connection failed: {e}")
        return False