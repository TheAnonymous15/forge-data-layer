# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Organization Models
=================================================
Organization and employer models.
"""
import uuid
from django.db import models
from django.conf import settings

# Import partner models to make them available
from .partner_models import (
    PartnerUser, PartnerUserManager,
    PartnerSession, PartnerLoginHistory,
    PartnerEmailVerificationToken, PartnerPasswordResetToken
)


class Organization(models.Model):
    """Organization/Company model."""

    class Size(models.TextChoices):
        SOLO = '1', '1 employee'
        MICRO = '1-10', '1-10 employees'
        SMALL = '11-50', '11-50 employees'
        MEDIUM = '51-200', '51-200 employees'
        LARGE = '201-500', '201-500 employees'
        ENTERPRISE = '500+', '500+ employees'

    class Type(models.TextChoices):
        COMPANY = 'company', 'Company'
        STARTUP = 'startup', 'Startup'
        NON_PROFIT = 'non_profit', 'Non-Profit'
        GOVERNMENT = 'government', 'Government'
        EDUCATIONAL = 'educational', 'Educational'
        NGO = 'ngo', 'NGO'
        OTHER = 'other', 'Other'

    class Industry(models.TextChoices):
        TECHNOLOGY = 'technology', 'Technology'
        FINANCE = 'finance', 'Finance & Banking'
        HEALTHCARE = 'healthcare', 'Healthcare'
        EDUCATION = 'education', 'Education'
        MANUFACTURING = 'manufacturing', 'Manufacturing'
        CONSULTING = 'consulting', 'Consulting'
        RETAIL = 'retail', 'Retail & E-commerce'
        MEDIA = 'media', 'Media & Entertainment'
        AGRICULTURE = 'agriculture', 'Agriculture'
        ENERGY = 'energy', 'Energy & Utilities'
        TRANSPORTATION = 'transportation', 'Transportation'
        HOSPITALITY = 'hospitality', 'Hospitality'
        LEGAL = 'legal', 'Legal Services'
        NGO = 'ngo', 'NGO / Non-Profit'
        GOVERNMENT = 'government', 'Government'
        OTHER = 'other', 'Other'

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = 'unverified', 'Unverified'
        PENDING = 'pending', 'Pending Verification'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Info
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)
    tagline = models.CharField(max_length=200, null=True, blank=True)

    # Classification
    org_type = models.CharField(max_length=20, choices=Type.choices, default=Type.COMPANY)
    size = models.CharField(max_length=20, choices=Size.choices, null=True, blank=True)
    industry = models.CharField(max_length=100, choices=Industry.choices, null=True, blank=True)
    industry_other = models.CharField(max_length=100, null=True, blank=True)  # When industry='other'
    founded_year = models.IntegerField(null=True, blank=True)

    # Contact
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(null=True, blank=True)

    # Location
    headquarters_country = models.CharField(max_length=100, null=True, blank=True)
    headquarters_city = models.CharField(max_length=100, null=True, blank=True)
    headquarters_address = models.TextField(null=True, blank=True)

    # Social Links
    linkedin_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)

    # Media
    logo_url = models.URLField(null=True, blank=True)
    cover_image_url = models.URLField(null=True, blank=True)

    # Interest/Looking for (from registration) - JSON array
    interest_types = models.JSONField(default=list, blank=True)  # ['hire_talent', 'internships', 'volunteer', 'partnership']
    
    # Initial needs/message from registration
    initial_message = models.TextField(null=True, blank=True)
    
    # Referral tracking
    referral_source = models.CharField(max_length=50, null=True, blank=True)  # social_media, referral, google, linkedin, event, other

    # Status
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Stats
    total_opportunities = models.IntegerField(default=0)
    total_hires = models.IntegerField(default=0)

    # Owner (the partner user who created/registered the organization)
    # Using UUID field since PartnerUser is in the same app and we want to avoid circular imports
    owner_id = models.UUIDField(null=True, blank=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    """Organization team members."""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        RECRUITER = 'recruiter', 'Recruiter'
        HIRING_MANAGER = 'hiring_manager', 'Hiring Manager'
        VIEWER = 'viewer', 'Viewer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECRUITER)
    title = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_org_invites'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = ['organization', 'user']

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class OrganizationLocation(models.Model):
    """Organization office locations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100)  # e.g., "Cape Town Office"
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField(null=True, blank=True)
    is_headquarters = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_locations'

    def __str__(self):
        return f"{self.organization.name} - {self.name}"

