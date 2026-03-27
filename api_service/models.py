# -*- coding: utf-8 -*-
"""
ForgeForth Africa - API Service Models
======================================
Models for API Service user management and access requests.
"""
import uuid
import hashlib
from django.db import models
from django.utils import timezone


class ServiceUserManager(models.Manager):
    """Manager for service users."""

    def create_user(self, username, email, password, **extra_fields):
        """Create a service user with hashed password."""
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')

        user = self.model(
            username=username.lower(),
            email=email.lower(),
            password_hash=self._hash_password(password),
            **extra_fields
        )
        user.save(using=self._db)
        return user

    def _hash_password(self, password):
        """Hash password using SHA-256 with salt."""
        salt = 'forgeforth_secure_salt_2026'
        return hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()


class APIServiceUser(models.Model):
    """
    Users who can access the API Service documentation and health dashboards.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        DEVELOPER = 'developer', 'Developer'
        VIEWER = 'viewer', 'Read-Only Viewer'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    password_hash = models.CharField(max_length=128)

    # Profile
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, null=True, blank=True)
    organization = models.CharField(max_length=200, null=True, blank=True)

    # Access control
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_default_password = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Metadata
    login_count = models.IntegerField(default=0)
    notes = models.TextField(null=True, blank=True)

    objects = ServiceUserManager()

    class Meta:
        db_table = 'api_service_users'
        verbose_name = 'API Service User'
        verbose_name_plural = 'API Service Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.role})"

    def check_password(self, password):
        """Verify password against stored hash."""
        salt = 'forgeforth_secure_salt_2026'
        return self.password_hash == hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()

    def set_password(self, password):
        """Set a new password."""
        salt = 'forgeforth_secure_salt_2026'
        self.password_hash = hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()

    def update_login(self):
        """Update login timestamp and count."""
        self.last_login = timezone.now()
        self.login_count += 1
        self.save(update_fields=['last_login', 'login_count'])


class APIServiceAccessRequest(models.Model):
    """
    Access requests for API Service.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class RequestedRole(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        DEVELOPER = 'developer', 'Developer'
        VIEWER = 'viewer', 'Viewer/Read-Only'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Request details
    requested_role = models.CharField(max_length=20, choices=RequestedRole.choices, default=RequestedRole.VIEWER)

    # Applicant info
    full_name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    organization = models.CharField(max_length=200, null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)

    # Request reason
    reason = models.TextField(help_text="Why do you need access?")
    intended_use = models.TextField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Admin response
    reviewed_by = models.CharField(max_length=150, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    # If approved, the created user
    created_user_id = models.UUIDField(null=True, blank=True)
    created_username = models.CharField(max_length=50, null=True, blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_service_access_requests'
        verbose_name = 'API Service Access Request'
        verbose_name_plural = 'API Service Access Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - API Service ({self.status})"

    def approve(self, admin_username, notes=None):
        """Approve the request."""
        self.status = self.Status.APPROVED
        self.reviewed_by = admin_username
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()

    def reject(self, admin_username, reason):
        """Reject the request."""
        self.status = self.Status.REJECTED
        self.reviewed_by = admin_username
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class APIServiceAuditLog(models.Model):
    """Audit log for API Service operations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True)
    username = models.CharField(max_length=50, null=True, blank=True)
    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100, null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_service_audit_logs'
        verbose_name = 'API Service Audit Log'
        verbose_name_plural = 'API Service Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.resource_type} by {self.username}"
