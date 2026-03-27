# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Database Router
==============================================
Routes database operations to the appropriate database
when running in multi-database mode.
"""


class DataLayerRouter:
    """
    Database router for multi-database mode.
    Routes models to their appropriate databases.
    """

    # Mapping of app labels to database aliases
    APP_DB_MAP = {
        'users': 'accounts_db',
        'auth': 'accounts_db',
        'contenttypes': 'default',
        'sessions': 'default',
        'admin': 'default',
        'profiles': 'profiles_db',
        'organizations': 'organizations_db',
        'opportunities': 'opportunities_db',
        'applications': 'applications_db',
        'tokens': 'tokens_db',
        'audit': 'audit_db',
    }

    def db_for_read(self, model, **hints):
        """Point read operations to the appropriate database."""
        return self.APP_DB_MAP.get(model._meta.app_label, 'default')

    def db_for_write(self, model, **hints):
        """Point write operations to the appropriate database."""
        return self.APP_DB_MAP.get(model._meta.app_label, 'default')

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are in the same database.
        For cross-database relations, use UUIDs instead of foreign keys.
        """
        db1 = self.APP_DB_MAP.get(obj1._meta.app_label, 'default')
        db2 = self.APP_DB_MAP.get(obj2._meta.app_label, 'default')
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations run on the correct database."""
        target_db = self.APP_DB_MAP.get(app_label, 'default')
        return db == target_db

