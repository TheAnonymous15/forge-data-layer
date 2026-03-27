# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Partner User Models
=======================================
Separate user model for partners/employers.
Partners are organization representatives, NOT talents.
"""
import uuid
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone


class PartnerUserManager(models.Manager):
    """Manager for PartnerUser model."""

    def create_partner(self, email, password, organization, **extra_fields):
        """Create and return a partner user."""
        if not email:
            raise ValueError('Partner users must have an email address')
        if not organization:
            raise ValueError('Partner users must be linked to an organization')

        email = email.lower().strip()
        partner = self.model(
            email=email,
            organization=organization,
            **extra_fields
        )
        partner.set_password(password)
        partner.save(using=self._db)
        return partner


class PartnerUser(models.Model):
    """
    Partner/Employer User model.
    
    This is SEPARATE from the talent User model.
    Partners represent organizations and have different attributes.
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Hiring Manager'
        RECRUITER = 'recruiter', 'Recruiter'
        MEMBER = 'member', 'Team Member'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=255)
    
    # Personal Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_code = models.CharField(max_length=10, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    
    # Organization Link (Required for partners)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='partner_users'
    )
    
    # Role within organization
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    
    # Permissions
    can_post_opportunities = models.BooleanField(default=True)
    can_manage_applications = models.BooleanField(default=True)
    can_manage_team = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_primary_contact = models.BooleanField(default=False)  # Main org contact
    
    # Authorization consent
    consent_authorized = models.BooleanField(default=False)  # Authorized to act for org
    consent_terms_accepted = models.BooleanField(default=False)
    consent_data_processing = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=255, null=True, blank=True)
    
    # Security
    last_login = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    registration_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PartnerUserManager()

    class Meta:
        db_table = 'partner_users'
        verbose_name = 'Partner User'
        verbose_name_plural = 'Partner Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['organization']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'is_verified']),
        ]

    def __str__(self):
        return f"{self.email} ({self.organization.name})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, raw_password):
        """Hash and set the password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Check the password against the hash."""
        return check_password(raw_password, self.password)

    def is_locked(self):
        """Check if account is locked."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_login(self):
        """Increment failed login attempts and lock if necessary."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=15)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def reset_failed_login(self):
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])

    def has_permission(self, permission):
        """Check if user has a specific permission."""
        if self.role == self.Role.OWNER:
            return True
        if self.role == self.Role.ADMIN:
            return True
        
        permission_map = {
            'post_opportunities': self.can_post_opportunities,
            'manage_applications': self.can_manage_applications,
            'manage_team': self.can_manage_team,
            'manage_settings': self.can_manage_settings,
            'view_analytics': self.can_view_analytics,
        }
        return permission_map.get(permission, False)


class PartnerSession(models.Model):
    """Session tracking for partner users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(PartnerUser, on_delete=models.CASCADE, related_name='sessions')
    
    token_hash = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=20, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'partner_sessions'
        ordering = ['-created_at']


class PartnerLoginHistory(models.Model):
    """Login history for partner users."""
    
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        LOCKED = 'locked', 'Account Locked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(PartnerUser, on_delete=models.CASCADE, related_name='login_history', null=True, blank=True)
    email = models.EmailField()  # Store email even if user doesn't exist
    
    status = models.CharField(max_length=20, choices=Status.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    failure_reason = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'partner_login_history'
        ordering = ['-created_at']


class PartnerEmailVerificationToken(models.Model):
    """Email verification tokens for partner users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(PartnerUser, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=255, unique=True)
    
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'partner_email_verification_tokens'
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user, expires_hours=24):
        """Create a verification token for a partner user."""
        import secrets
        from datetime import timedelta
        
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=expires_hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        if self.is_used:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    def mark_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class PartnerPasswordResetToken(models.Model):
    """Password reset tokens for partner users."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(PartnerUser, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'partner_password_reset_tokens'
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user, expires_hours=2):
        """Create a password reset token for a partner user."""
        import secrets
        from datetime import timedelta
        
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=expires_hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if token is valid."""
        if self.is_used:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    def mark_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

