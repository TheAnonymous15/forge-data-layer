# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Token Models
===========================================
Models for verification tokens, password reset, and 2FA sessions.
"""
import uuid
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.conf import settings


class BaseToken(models.Model):
    """Abstract base model for tokens."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)s_tokens'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and timezone.now() < self.expires_at

    def mark_used(self):
        """Mark token as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])

    @classmethod
    def generate_token(cls):
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)


class EmailVerificationToken(BaseToken):
    """Email verification token model."""

    email = models.EmailField()

    class Meta:
        db_table = 'email_verification_tokens'
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Verification for {self.email}"

    @classmethod
    def create_for_user(cls, user, expires_hours=24):
        """Create a new verification token for a user."""
        # Invalidate existing tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        return cls.objects.create(
            user=user,
            email=user.email,
            token=cls.generate_token(),
            expires_at=timezone.now() + timedelta(hours=expires_hours)
        )


class PasswordResetToken(BaseToken):
    """Password reset token model."""

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Password reset for {self.user.email}"

    @classmethod
    def create_for_user(cls, user, ip_address=None, expires_hours=2):
        """Create a new password reset token for a user."""
        # Invalidate existing tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        return cls.objects.create(
            user=user,
            token=cls.generate_token(),
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(hours=expires_hours)
        )


class TwoFactorSession(models.Model):
    """Temporary 2FA session during login flow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='two_factor_sessions'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'two_factor_sessions'
        verbose_name = '2FA Session'
        verbose_name_plural = '2FA Sessions'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"2FA session for {self.user.email}"

    def is_valid(self):
        return timezone.now() < self.expires_at

    @classmethod
    def create_for_user(cls, user, ip_address=None, expires_minutes=5):
        """Create a new 2FA session."""
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(minutes=expires_minutes)
        )


class TwoFactorBackupCode(models.Model):
    """2FA backup codes for account recovery."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='backup_codes'
    )
    code_hash = models.CharField(max_length=255)  # Hashed backup code
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'two_factor_backup_codes'
        verbose_name = '2FA Backup Code'
        verbose_name_plural = '2FA Backup Codes'

    def __str__(self):
        return f"Backup code for {self.user.email}"

    def mark_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class EmailOTP(models.Model):
    """Email-based OTP for 2FA."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_otps'
    )
    code = models.CharField(max_length=6)  # 6-digit code
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_otps'
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'
        indexes = [
            models.Index(fields=['user', 'code', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.user.email}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at and self.attempts < 3

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    @classmethod
    def create_for_user(cls, user, expires_minutes=10):
        """Create a new email OTP."""
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Invalidate existing OTPs
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        return cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=expires_minutes)
        )

