# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Opportunity Models
=================================================
Job/Opportunity listings.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Opportunity(models.Model):
    """Job/Opportunity listing."""

    class OpportunityType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'
        CONTRACT = 'contract', 'Contract'
        FREELANCE = 'freelance', 'Freelance'
        INTERNSHIP = 'internship', 'Internship'
        VOLUNTEER = 'volunteer', 'Volunteer'
        APPRENTICESHIP = 'apprenticeship', 'Apprenticeship'

    class ExperienceLevel(models.TextChoices):
        ENTRY = 'entry', 'Entry Level'
        JUNIOR = 'junior', 'Junior'
        MID = 'mid', 'Mid-Level'
        SENIOR = 'senior', 'Senior'
        LEAD = 'lead', 'Lead/Principal'
        EXECUTIVE = 'executive', 'Executive'

    class RemotePolicy(models.TextChoices):
        ONSITE = 'onsite', 'On-site Only'
        REMOTE = 'remote', 'Remote Only'
        HYBRID = 'hybrid', 'Hybrid'
        FLEXIBLE = 'flexible', 'Flexible'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAUSED = 'paused', 'Paused'
        CLOSED = 'closed', 'Closed'
        FILLED = 'filled', 'Filled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True)
    summary = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField()

    # Organization
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='opportunities'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='posted_opportunities'
    )

    # Classification
    opportunity_type = models.CharField(max_length=20, choices=OpportunityType.choices)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices)
    category = models.CharField(max_length=100, null=True, blank=True)

    # Location
    location = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    remote_policy = models.CharField(max_length=20, choices=RemotePolicy.choices, default=RemotePolicy.ONSITE)

    # Compensation
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='ZAR')
    salary_period = models.CharField(max_length=20, default='yearly')  # hourly, monthly, yearly
    hide_salary = models.BooleanField(default=False)
    benefits = models.JSONField(default=list, blank=True)

    # Requirements
    requirements = models.TextField(null=True, blank=True)
    qualifications = models.TextField(null=True, blank=True)
    responsibilities = models.TextField(null=True, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    min_experience_years = models.IntegerField(default=0)

    # Settings
    positions_available = models.IntegerField(default=1)
    external_apply_url = models.URLField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)

    # Dates
    start_date = models.DateField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Stats
    views_count = models.IntegerField(default=0)
    applications_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'opportunities'
        verbose_name = 'Opportunity'
        verbose_name_plural = 'Opportunities'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.title} at {self.organization.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.organization.name}")
            self.slug = f"{base_slug}-{str(self.id)[:8]}" if self.id else base_slug
        super().save(*args, **kwargs)


class SavedOpportunity(models.Model):
    """Opportunities saved by talents."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_opportunities'
    )
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_opportunities'
        unique_together = ['user', 'opportunity']

    def __str__(self):
        return f"{self.user.email} saved {self.opportunity.title}"

