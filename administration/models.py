# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Administration Models
====================================================
Staff roles, feature flags, admin audit logs, and support tickets.
"""
import uuid
from django.db import models
from django.conf import settings


class StaffRole(models.Model):
    """Staff roles with granular permissions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Role details
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Permissions (array of permission strings)
    permissions = models.JSONField(default=list, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Hierarchy
    level = models.PositiveIntegerField(default=0)  # Higher = more permissions

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_roles'
        ordering = ['-level', 'name']

    def __str__(self):
        return self.name


class StaffRoleAssignment(models.Model):
    """Assignment of staff roles to users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_role_assignments'
    )
    role = models.ForeignKey(StaffRole, on_delete=models.CASCADE, related_name='assignments')

    # Assignment metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='role_assignments_made'
    )
    reason = models.TextField(blank=True)

    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'staff_role_assignments'
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


class FeatureFlag(models.Model):
    """Feature flags for controlled rollouts and A/B testing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Flag details
    name = models.CharField(max_length=100, unique=True, db_index=True)
    key = models.CharField(max_length=100, unique=True)  # Code-friendly key
    description = models.TextField(blank=True)

    # Status
    is_enabled = models.BooleanField(default=False)

    # Rollout control
    rollout_percentage = models.PositiveIntegerField(default=0)  # 0-100
    target_users = models.JSONField(default=list, blank=True)  # Specific user IDs
    target_roles = models.JSONField(default=list, blank=True)  # Specific roles

    # Environment
    environments = models.JSONField(default=list, blank=True)  # ['dev', 'staging', 'prod']

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    enabled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'feature_flags'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({'ON' if self.is_enabled else 'OFF'})"


class AdminAuditLog(models.Model):
    """Audit log for all admin actions."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'
        SUSPEND = 'suspend', 'Suspend'
        RESTORE = 'restore', 'Restore'
        EXPORT = 'export', 'Export'
        IMPORT = 'import', 'Import'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions'
    )
    user_email = models.EmailField()  # Store email in case user is deleted

    # What
    action = models.CharField(max_length=100, choices=Action.choices)
    description = models.TextField(blank=True)

    # Where (entity affected)
    entity_type = models.CharField(max_length=100, db_index=True)  # user, opportunity, application, etc.
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True)  # String representation

    # Changes
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'admin_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user_email} {self.action} {self.entity_type}"


class SupportTicket(models.Model):
    """Support tickets and help requests."""

    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Technical Issue'
        ACCOUNT = 'account', 'Account Issue'
        BILLING = 'billing', 'Billing'
        FEATURE_REQUEST = 'feature_request', 'Feature Request'
        BUG = 'bug', 'Bug Report'
        GENERAL = 'general', 'General Inquiry'
        OTHER = 'other', 'Other'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        WAITING_USER = 'waiting_user', 'Waiting on User'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Ticket details
    ticket_number = models.CharField(max_length=20, unique=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )

    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.GENERAL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_support_tickets'
    )

    # Resolution
    resolution = models.TextField(blank=True)

    # Attachments
    attachments = models.JSONField(default=list, blank=True)

    # Tags
    tags = models.JSONField(default=list, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['priority', '-created_at']),
        ]

    def __str__(self):
        return f"#{self.ticket_number} - {self.subject}"


class SupportTicketComment(models.Model):
    """Comments/replies on support tickets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    comment = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal staff notes
    attachments = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_ticket_comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
        ]

    def __str__(self):
        return f"Comment on {self.ticket.ticket_number} by {self.user.email}"

