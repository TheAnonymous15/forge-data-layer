# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Media Models
============================================
Models for documents, images, and media files
"""
import os
import uuid
from django.db import models
from django.conf import settings


def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    ext = filename.split('.')[-1]
    new_filename = f"{instance.id}.{ext}"
    return os.path.join('documents', str(instance.owner_id), new_filename)


def image_upload_path(instance, filename):
    """Generate upload path for images"""
    ext = filename.split('.')[-1]
    new_filename = f"{instance.id}.{ext}"
    return os.path.join('images', str(instance.owner_id), new_filename)


class Document(models.Model):
    """Document model for CVs, certificates, etc."""

    DOCUMENT_TYPES = [
        ('cv', 'CV/Resume'),
        ('cover_letter', 'Cover Letter'),
        ('certificate', 'Certificate'),
        ('transcript', 'Transcript'),
        ('portfolio', 'Portfolio'),
        ('id_document', 'ID Document'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Processing Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.UUIDField(db_index=True)  # User ID from users app

    # File info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')

    # Original file
    original_file = models.FileField(upload_to=document_upload_path, null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    original_size = models.BigIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=100)

    # Processed content
    extracted_text = models.TextField(blank=True)
    parsed_data = models.JSONField(default=dict, blank=True)  # AI-extracted data

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True)

    # Flags
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner_id', 'document_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.document_type})"


class Image(models.Model):
    """Image model for profile photos, gallery, etc."""

    IMAGE_TYPES = [
        ('profile', 'Profile Photo'),
        ('cover', 'Cover Photo'),
        ('gallery', 'Gallery'),
        ('logo', 'Logo'),
        ('certificate', 'Certificate Image'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Processing Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.UUIDField(db_index=True)  # User/Organization ID
    owner_type = models.CharField(max_length=20, default='user')  # user, organization

    # File info
    title = models.CharField(max_length=255, blank=True)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='other')

    # Original image
    original_file = models.ImageField(upload_to=image_upload_path, null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    original_size = models.BigIntegerField(default=0)  # in bytes
    original_width = models.IntegerField(default=0)
    original_height = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100)

    # Processed versions (WebP)
    thumbnail_url = models.URLField(blank=True)  # 150x150
    medium_url = models.URLField(blank=True)     # 400x400
    large_url = models.URLField(blank=True)      # 800x800
    full_url = models.URLField(blank=True)       # Original size, WebP

    # Processed sizes
    thumbnail_size = models.BigIntegerField(default=0)
    medium_size = models.BigIntegerField(default=0)
    large_size = models.BigIntegerField(default=0)
    full_size = models.BigIntegerField(default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True)

    # Flags
    is_primary = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'images'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner_id', 'owner_type', 'image_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.image_type})"


class MediaProcessingLog(models.Model):
    """Log all media processing operations for audit"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    media_type = models.CharField(max_length=20)  # document, image
    media_id = models.UUIDField()

    operation = models.CharField(max_length=50)  # upload, sanitize, compress, parse, etc.
    status = models.CharField(max_length=20)  # success, failed

    input_size = models.BigIntegerField(default=0)
    output_size = models.BigIntegerField(default=0)

    processing_time_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_processing_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['media_type', 'media_id']),
            models.Index(fields=['operation', 'status']),
        ]

