# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Communications Models
====================================================
Notifications, messages, emails, and platform announcements.
"""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notifications for in-app, email, SMS, and push."""

    class Type(models.TextChoices):
        APPLICATION = 'application', 'Application Update'
        INTERVIEW = 'interview', 'Interview'
        OPPORTUNITY = 'opportunity', 'New Opportunity'
        MESSAGE = 'message', 'Message'
        SYSTEM = 'system', 'System'
        REMINDER = 'reminder', 'Reminder'
        ACHIEVEMENT = 'achievement', 'Achievement'
        PROFILE = 'profile', 'Profile'
        MATCH = 'match', 'Match Found'

    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In-App'
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push Notification'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        READ = 'read', 'Read'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Notification details
    notif_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)

    title = models.CharField(max_length=200)
    body = models.TextField()
    action_url = models.URLField(blank=True)
    action_label = models.CharField(max_length=100, blank=True)

    # Additional data
    data = models.JSONField(default=dict, blank=True)

    # Reference to related object
    ref_type = models.CharField(max_length=50, blank=True)  # application, opportunity, message, etc.
    ref_id = models.UUIDField(null=True, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['status']),
            models.Index(fields=['ref_type', 'ref_id']),
        ]

    def __str__(self):
        return f"{self.recipient.email} - {self.title}"


class EmailLog(models.Model):
    """Detailed email sending logs and tracking."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        BOUNCED = 'bounced', 'Bounced'
        COMPLAINED = 'complained', 'Spam Complaint'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Recipient
    recipient_email = models.EmailField(db_index=True)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs'
    )

    # Email content
    subject = models.CharField(max_length=500)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)

    # Template info
    template_name = models.CharField(max_length=100, blank=True)
    template_context = models.JSONField(default=dict, blank=True)

    # Attachments
    attachments = models.JSONField(default=list, blank=True)

    # Sending metadata
    from_email = models.EmailField(blank=True)
    reply_to = models.EmailField(blank=True)

    # Status and tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)

    # External provider info
    provider = models.CharField(max_length=50, blank=True)  # sendgrid, ses, etc.
    provider_message_id = models.CharField(max_length=255, blank=True)

    # Tracking events
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    complained_at = models.DateTimeField(null=True, blank=True)

    # Analytics
    open_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['template_name']),
            models.Index(fields=['-sent_at']),
        ]

    def __str__(self):
        return f"{self.recipient_email} - {self.subject}"


class Message(models.Model):
    """Internal messaging system between users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Participants
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )

    # Content
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    attachments = models.JSONField(default=list, blank=True)

    # Threading
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    thread_id = models.UUIDField(default=uuid.uuid4, db_index=True)

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Archiving (soft delete per user)
    is_archived_sender = models.BooleanField(default=False)
    is_archived_recipient = models.BooleanField(default=False)
    is_deleted_sender = models.BooleanField(default=False)
    is_deleted_recipient = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['thread_id', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender.email} -> {self.recipient.email}: {self.subject or 'No subject'}"


class Announcement(models.Model):
    """Platform-wide announcements and system messages."""

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Content
    title = models.CharField(max_length=200)
    content = models.TextField()
    content_html = models.TextField(blank=True)

    # Display settings
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    is_dismissible = models.BooleanField(default=True)
    show_on_dashboard = models.BooleanField(default=True)

    # Targeting
    target_roles = models.JSONField(default=list, blank=True)  # ['talent', 'employer', etc.]
    target_users = models.JSONField(default=list, blank=True)  # Specific user IDs

    # Scheduling
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Author
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_announcements'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['is_active', '-published_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return self.title


class AnnouncementView(models.Model):
    """Track which users have viewed/dismissed announcements."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcement_views')

    is_dismissed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(auto_now_add=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'announcement_views'
        unique_together = ['announcement', 'user']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.email} viewed {self.announcement.title}"

