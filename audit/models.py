# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Audit Models
==========================================
Audit logging for security and compliance.
"""
import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Comprehensive audit log for all data operations."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        READ = 'read', 'Read'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        EXPORT = 'export', 'Export'
        IMPORT = 'import', 'Import'

    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Actor
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    service_id = models.CharField(max_length=50, null=True, blank=True)  # For service-to-service calls

    # Action
    action = models.CharField(max_length=20, choices=Action.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)

    # Target
    resource_type = models.CharField(max_length=100)  # e.g., 'User', 'Application'
    resource_id = models.CharField(max_length=50, null=True, blank=True)

    # Details
    description = models.TextField(null=True, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_id = models.CharField(max_length=50, null=True, blank=True)

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['service_id', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} {self.resource_type} by {self.user or self.service_id}"


class DataAccessLog(models.Model):
    """Track data access for compliance (POPIA, GDPR, etc.)."""

    class Purpose(models.TextChoices):
        DISPLAY = 'display', 'Display'
        EXPORT = 'export', 'Export'
        ANALYTICS = 'analytics', 'Analytics'
        MATCHING = 'matching', 'Matching'
        COMPLIANCE = 'compliance', 'Compliance'
        SUPPORT = 'support', 'Support'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who accessed
    accessor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_access_logs'
    )
    accessor_service = models.CharField(max_length=50, null=True, blank=True)

    # Whose data
    data_subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_accessed_logs'
    )

    # What was accessed
    data_categories = models.JSONField(default=list)  # ['email', 'phone', 'address', etc.]
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    legal_basis = models.CharField(max_length=100, null=True, blank=True)  # Consent, Contract, etc.

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'data_access_logs'
        verbose_name = 'Data Access Log'
        verbose_name_plural = 'Data Access Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.accessor_user or self.accessor_service} accessed {self.data_subject_user}'s data"

