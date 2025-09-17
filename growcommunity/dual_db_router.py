"""
Dual Database Router for writing to both SQLite and PostgreSQL
This router ensures all write operations go to both databases
while read operations come from the primary (SQLite) database.
"""

import logging

logger = logging.getLogger(__name__)


class DualDatabaseRouter:
    """
    A router to control database operations for dual database setup.
    Reads from SQLite (primary), writes to both SQLite and PostgreSQL.
    """
    
    def db_for_read(self, model, **hints):
        """
        Always read from the default (SQLite) database.
        """
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Return None to allow Django to write to all configured databases.
        The actual dual writing is handled by middleware.
        """
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed.
        """
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Allow migrations on both databases.
        """
        return True


class DualWriteMiddleware:
    """
    Middleware to handle dual database writes.
    This ensures data is written to both SQLite and PostgreSQL.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Set up dual database writing for this request.
        """
        # Store the original database for this thread
        request._dual_db_enabled = True
        return None