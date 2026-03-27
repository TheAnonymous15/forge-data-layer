# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Security Models
==============================================
API keys, security events, consent records, and IP blocking.
"""
import uuid
from django.db import models
from django.conf import settings


class APIKey(models.Model):
    """API keys for programmatic access and service authentication."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Owner
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='api_keys'
    )

    # Key details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Key data (never store the actual key, only hash)
    key_prefix = models.CharField(max_length=10, db_index=True)  # First chars for identification
    key_hash = models.CharField(max_length=128, unique=True, db_index=True)  # Hashed key

    # Permissions and restrictions
    permissions = models.JSONField(default=list, blank=True)  # List of allowed operations
    allowed_ips = models.JSONField(default=list, blank=True)  # IP whitelist
    allowed_origins = models.JSONField(default=list, blank=True)  # CORS origins
    rate_limit = models.PositiveIntegerField(default=1000)  # Requests per hour

    # Status
    is_active = models.BooleanField(default=True)

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)

    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['key_prefix']),
            models.Index(fields=['is_active', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"


class SecurityEvent(models.Model):
    """Security events, incidents, and threats."""

    class EventType(models.TextChoices):
        LOGIN_FAILED = 'login_failed', 'Failed Login'
        LOGIN_SUSPICIOUS = 'login_suspicious', 'Suspicious Login'
        UNAUTHORIZED_ACCESS = 'unauthorized_access', 'Unauthorized Access'
        RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded', 'Rate Limit Exceeded'
        INVALID_TOKEN = 'invalid_token', 'Invalid Token'
        DATA_BREACH_ATTEMPT = 'data_breach_attempt', 'Data Breach Attempt'
        SQL_INJECTION = 'sql_injection', 'SQL Injection Attempt'
        XSS_ATTEMPT = 'xss_attempt', 'XSS Attempt'
        BRUTEFORCE = 'bruteforce', 'Brute Force Attack'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Event details
    event_type = models.CharField(max_length=100, choices=EventType.choices, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)

    # Context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_method = models.CharField(max_length=10, blank=True)

    # Description
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)

    # Resolution
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events'
    )
    resolution_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['is_resolved', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.severity}"


class ConsentRecord(models.Model):
    """User consent records for POPIA/GDPR compliance."""

    class ConsentType(models.TextChoices):
        TERMS_OF_SERVICE = 'terms_of_service', 'Terms of Service'
        PRIVACY_POLICY = 'privacy_policy', 'Privacy Policy'
        MARKETING = 'marketing', 'Marketing Communications'
        DATA_PROCESSING = 'data_processing', 'Data Processing'
        COOKIES = 'cookies', 'Cookies'
        THIRD_PARTY_SHARING = 'third_party_sharing', 'Third-party Sharing'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consent_records'
    )

    # Consent details
    consent_type = models.CharField(max_length=100, choices=ConsentType.choices, db_index=True)
    version = models.CharField(max_length=50)  # Version of policy/terms

    # Status
    is_granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Additional data
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'consent_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'consent_type']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['consent_type', 'version']),
        ]

    def __str__(self):
        status = 'Granted' if self.is_granted else 'Withdrawn'
        return f"{self.user.email} - {self.consent_type} - {status}"


class BlockedIP(models.Model):
    """Blocked IP addresses for security."""

    class BlockReason(models.TextChoices):
        ABUSE = 'abuse', 'Abuse'
        SPAM = 'spam', 'Spam'
        BRUTEFORCE = 'bruteforce', 'Brute Force'
        MALICIOUS = 'malicious', 'Malicious Activity'
        MANUAL = 'manual', 'Manual Block'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # IP details
    ip_address = models.GenericIPAddressField(unique=True, db_index=True)
    ip_range = models.CharField(max_length=50, blank=True)  # CIDR notation

    # Block details
    reason = models.CharField(max_length=50, choices=BlockReason.choices, default=BlockReason.MANUAL)
    description = models.TextField(blank=True)

    # Metadata
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_ips'
    )

    # Automatic unblock
    is_permanent = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Statistics
    block_count = models.PositiveIntegerField(default=0)  # Number of blocked requests
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'blocked_ips'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.reason}"


class RateLimitLog(models.Model):
    """Track rate limit violations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(db_index=True)

    # What
    endpoint = models.CharField(max_length=500)
    limit_type = models.CharField(max_length=50)  # hourly, daily, per_endpoint, etc.
    limit_value = models.PositiveIntegerField()
    current_count = models.PositiveIntegerField()

    # When
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'rate_limit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['endpoint', '-created_at']),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.endpoint} - {self.current_count}/{self.limit_value}"

