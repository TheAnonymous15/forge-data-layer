# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Storage Models
==============================================
File storage, buckets, and access management.
"""
import uuid
from django.db import models
from django.conf import settings


class StorageBucket(models.Model):
    """Storage bucket for organizing files."""

    class BucketType(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'
        PROTECTED = 'protected', 'Protected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    bucket_type = models.CharField(max_length=20, choices=BucketType.choices, default=BucketType.PRIVATE)
    description = models.TextField(blank=True)

    # Settings
    max_file_size = models.BigIntegerField(default=104857600)  # 100MB
    allowed_extensions = models.JSONField(default=list, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    total_files = models.PositiveIntegerField(default=0)
    total_size = models.BigIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'storage_buckets'
        ordering = ['name']

    def __str__(self):
        return self.name


class StoredFile(models.Model):
    """Stored file record."""

    class Status(models.TextChoices):
        UPLOADING = 'uploading', 'Uploading'
        PROCESSING = 'processing', 'Processing'
        AVAILABLE = 'available', 'Available'
        ARCHIVED = 'archived', 'Archived'
        DELETED = 'deleted', 'Deleted'
        ERROR = 'error', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(StorageBucket, on_delete=models.CASCADE, related_name='files')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stored_files'
    )

    # File info
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    extension = models.CharField(max_length=20, blank=True)
    size = models.BigIntegerField(default=0)

    # Storage location
    storage_path = models.CharField(max_length=500)
    storage_url = models.URLField(blank=True, max_length=1000)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=64, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADING)
    error_message = models.TextField(blank=True)

    # Processing info
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'stored_files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bucket', '-created_at']),
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['content_type']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.bucket.name})"


class FileAccess(models.Model):
    """File access logs and permissions."""

    class AccessType(models.TextChoices):
        READ = 'read', 'Read'
        WRITE = 'write', 'Write'
        DELETE = 'delete', 'Delete'
        SHARE = 'share', 'Share'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(StoredFile, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_access_logs'
    )

    access_type = models.CharField(max_length=20, choices=AccessType.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Timestamps
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_access_logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['file', '-accessed_at']),
            models.Index(fields=['user', '-accessed_at']),
        ]

    def __str__(self):
        return f"{self.file.filename} - {self.access_type}"


class ShareLink(models.Model):
    """Shareable links for files."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(StoredFile, on_delete=models.CASCADE, related_name='share_links')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_share_links'
    )

    # Link settings
    token = models.CharField(max_length=64, unique=True)
    password = models.CharField(max_length=128, blank=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    current_downloads = models.PositiveIntegerField(default=0)

    # Status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'share_links'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['file', '-created_at']),
        ]

    def __str__(self):
        return f"Share link for {self.file.filename}"

