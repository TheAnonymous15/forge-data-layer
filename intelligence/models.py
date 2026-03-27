# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Intelligence Models
==================================================
CV parsing, skill extraction, AI insights, and talent scoring.
"""
import uuid
from django.db import models
from django.conf import settings


class SkillTaxonomy(models.Model):
    """AI-enhanced skill taxonomy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    normalized_name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    # Relationships
    aliases = models.JSONField(default=list, blank=True)  # Alternative names
    related_skills = models.JSONField(default=list, blank=True)  # Related skill IDs

    # Market data
    demand_score = models.FloatField(default=0.0)  # 0-100
    trend = models.CharField(max_length=20, default='stable')  # growing, declining, stable

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'skill_taxonomy'
        verbose_name_plural = 'Skill Taxonomies'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class CVParseResult(models.Model):
    """Results from CV/resume parsing using AI."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cv_parses')

    # Source file
    source_file_url = models.URLField()
    source_file_name = models.CharField(max_length=255)

    # Extracted personal data
    extracted_name = models.CharField(max_length=200, blank=True)
    extracted_email = models.EmailField(blank=True)
    extracted_phone = models.CharField(max_length=50, blank=True)
    extracted_location = models.CharField(max_length=200, blank=True)
    extracted_summary = models.TextField(blank=True)

    # Structured data (JSON arrays)
    experience = models.JSONField(default=list, blank=True)  # Work experience entries
    education = models.JSONField(default=list, blank=True)  # Education entries
    skills = models.JSONField(default=list, blank=True)  # Extracted skills
    certifications = models.JSONField(default=list, blank=True)  # Certifications
    languages = models.JSONField(default=list, blank=True)  # Languages

    # Processing metadata
    confidence_score = models.FloatField(default=0.0)  # 0-1 confidence
    processing_time_ms = models.PositiveIntegerField(default=0)
    raw_text = models.TextField(blank=True)  # Extracted raw text

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cv_parse_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.source_file_name}"


class TalentScore(models.Model):
    """AI-computed talent scoring and profile quality assessment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='talent_scores')

    # Overall scores (0-100)
    overall_score = models.FloatField(default=0.0)
    skills_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=0.0)
    education_score = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0)
    engagement_score = models.FloatField(default=0.0)

    # Detailed breakdown
    breakdown = models.JSONField(default=dict, blank=True)

    # AI recommendations for improvement
    recommendations = models.JSONField(default=list, blank=True)

    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'talent_scores'
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['user', '-calculated_at']),
            models.Index(fields=['-overall_score']),
        ]

    def __str__(self):
        return f"{self.user.email} - Score: {self.overall_score:.1f}"


class SkillExtraction(models.Model):
    """Skill extraction from text using AI/NLP."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Source
    source_text = models.TextField()
    source_type = models.CharField(max_length=50)  # cv, job_description, profile, etc.
    source_id = models.UUIDField(null=True, blank=True)  # Reference to source object

    # Extracted data
    extracted_skills = models.JSONField(default=list)  # List of skill names/IDs
    confidence_scores = models.JSONField(default=dict)  # skill_id -> confidence

    # Processing metadata
    processing_time_ms = models.PositiveIntegerField(default=0)
    model_version = models.CharField(max_length=50, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'skill_extractions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Skill extraction from {self.source_type} - {len(self.extracted_skills)} skills"


class IntelligenceInsight(models.Model):
    """AI-generated insights and recommendations for users."""

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='intelligence_insights'
    )

    # Insight details
    insight_type = models.CharField(max_length=50)  # skill_gap, market_trend, profile_improvement, etc.
    title = models.CharField(max_length=200)
    content = models.TextField()
    data = models.JSONField(default=dict, blank=True)  # Additional structured data

    # Priority and actions
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    is_actionable = models.BooleanField(default=True)
    action_url = models.URLField(blank=True)
    action_label = models.CharField(max_length=100, blank=True)

    # User interaction
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    is_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)

    # Validity
    valid_until = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intelligence_insights'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['insight_type']),
            models.Index(fields=['is_dismissed', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.insight_type}: {self.title}"

