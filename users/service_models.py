# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Service Access Request Models
=================================================
Models for service access requests.

NOTE: APIServiceUser and DataLayerUser are defined in their respective apps:
- api_service.models.APIServiceUser
- data_layer.models.DataLayerUser
"""
import uuid
from django.db import models
from django.utils import timezone


# Re-export from authoritative sources for backward compatibility
from api_service.models import APIServiceUser
from data_layer.models import DataLayerUser


class ServiceAccessRequest(models.Model):
    """
    Access requests for API Service or Data Layer.
    """

    class ServiceType(models.TextChoices):
        API_SERVICE = 'api_service', 'API Service'
        DATA_LAYER = 'data_layer', 'Data Layer'

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
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    requested_role = models.CharField(max_length=20, choices=RequestedRole.choices, default=RequestedRole.VIEWER)

    # Applicant info
    full_name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    organization = models.CharField(max_length=200, null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)

    # Request reason
    reason = models.TextField(help_text="Why do you need access?")
    intended_use = models.TextField(null=True, blank=True, help_text="How will you use this access?")

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
        db_table = 'service_access_requests'
        verbose_name = 'Service Access Request'
        verbose_name_plural = 'Service Access Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.service_type} ({self.status})"

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
