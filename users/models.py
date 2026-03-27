# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer User Models
==========================================
Custom user model with all authentication-related fields.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for ForgeForth Africa.
    
    This model is for TALENTS only (individuals seeking opportunities).
    Partners/Employers use the separate PartnerUser model.

    Roles:
    - talent: Individual professionals seeking opportunities
hj    - admin: Platform administrators (can be removed if admins use separate system)
    """

    class Role(models.TextChoices):
        TALENT = 'talent', 'Talent'
        ADMIN = 'admin', 'Admin'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class EducationLevel(models.TextChoices):
        HIGH_SCHOOL = 'high_school', 'High School / Matric'
        CERTIFICATE = 'certificate', 'Certificate / Diploma'
        BACHELORS = 'bachelors', "Bachelor's Degree"
        MASTERS = 'masters', "Master's Degree"
        DOCTORATE = 'doctorate', 'Doctorate / PhD'
        SELF_TAUGHT = 'self_taught', 'Self-taught / Bootcamp'
        OTHER = 'other', 'Other'

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core fields
    email = models.EmailField(unique=True, db_index=True)
    phone_code = models.CharField(max_length=10, null=True, blank=True)  # e.g., +254, +27
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)

    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)  # Brief bio/about

    # Education & Career
    education_level = models.CharField(max_length=30, choices=EducationLevel.choices, null=True, blank=True)

    # Location
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)

    # Role & Status
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TALENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=255, null=True, blank=True)
    two_factor_method = models.CharField(max_length=20, null=True, blank=True)  # totp, email, sms

    # Profile metadata (JSON field for flexible data)
    metadata = models.JSONField(default=dict, blank=True)

    # Opportunity preferences (what they're looking for)
    opportunity_types = models.JSONField(default=list, blank=True)  # ['volunteer', 'internship', 'job', 'skillup']
    
    # Skills and fields (stored as JSON arrays, linked to profile later)
    skills = models.JSONField(default=list, blank=True)  # Selected skills during registration
    preferred_fields = models.JSONField(default=list, blank=True)  # Industry preferences
    
    # Referral tracking
    referral_source = models.CharField(max_length=50, null=True, blank=True)  # social_media, friend, google, etc.

    # Consent tracking
    consent_age_confirmed = models.BooleanField(default=False)  # Confirmed 18+ or guardian consent
    consent_data_processing = models.BooleanField(default=False)  # Data processing consent
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)

    # Security
    last_login = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    registration_ip = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

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
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class LoginHistory(models.Model):
    """Track login attempts for security and analytics."""

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REQUIRES_2FA = 'requires_2fa', 'Requires 2FA'
        BLOCKED = 'blocked', 'Blocked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='login_history')
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_history'
        verbose_name = 'Login History'
        verbose_name_plural = 'Login History'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        return f"{self.email} - {self.status} at {self.created_at}"


class UserSession(models.Model):
    """Track active user sessions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token_hash = models.CharField(max_length=255, unique=True)  # Hash of refresh token
    device_name = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)  # mobile, desktop, tablet
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.email} - {self.device_name or 'Unknown'}"

    def is_expired(self):
        return timezone.now() > self.expires_at
