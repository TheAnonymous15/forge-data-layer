# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Matching Models
==============================================
AI-powered talent-opportunity matching, recommendations, and search indexing.
"""
import uuid
from django.db import models
from django.conf import settings


class MatchScore(models.Model):
    """Computed match scores between talent and opportunities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Match participants
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_scores'
    )
    opportunity = models.ForeignKey(
        'opportunities.Opportunity',
        on_delete=models.CASCADE,
        related_name='match_scores'
    )

    # Overall match score (0-100)
    overall_score = models.FloatField(default=0.0, db_index=True)

    # Component scores (0-100 each)
    skills_match = models.FloatField(default=0.0)
    experience_match = models.FloatField(default=0.0)
    education_match = models.FloatField(default=0.0)
    location_match = models.FloatField(default=0.0)
    salary_match = models.FloatField(default=0.0)
    culture_match = models.FloatField(default=0.0)

    # Detailed breakdown
    breakdown = models.JSONField(default=dict, blank=True)

    # Skill analysis
    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    skill_gap_analysis = models.JSONField(default=dict, blank=True)

    # AI confidence
    confidence = models.FloatField(default=0.0)  # 0-1

    # Model info
    model_version = models.CharField(max_length=50, blank=True)

    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'match_scores'
        unique_together = ['user', 'opportunity']
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['user', '-overall_score']),
            models.Index(fields=['opportunity', '-overall_score']),
            models.Index(fields=['-overall_score']),
            models.Index(fields=['-calculated_at']),
        ]

    def __str__(self):
        return f"{self.user.email} <-> Opportunity {self.opportunity.id}: {self.overall_score:.1f}%"


class Recommendation(models.Model):
    """AI-generated recommendations for users."""

    class RecommendationType(models.TextChoices):
        OPPORTUNITY = 'opportunity', 'Opportunity'
        SKILL = 'skill', 'Skill to Learn'
        COURSE = 'course', 'Course'
        CONNECTION = 'connection', 'Connection'
        CONTENT = 'content', 'Content'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )

    # Recommendation details
    rec_type = models.CharField(
        max_length=50,
        choices=RecommendationType.choices,
        db_index=True
    )
    target_id = models.UUIDField(db_index=True)  # ID of recommended entity

    # Related match score (if applicable)
    match_score = models.ForeignKey(
        MatchScore,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Scoring
    relevance_score = models.FloatField(default=0.0, db_index=True)  # 0-100
    confidence = models.FloatField(default=0.0)  # 0-1

    # Explanation
    reason = models.TextField(blank=True)
    explanation_data = models.JSONField(default=dict, blank=True)

    # Ranking
    rank = models.PositiveIntegerField(default=0)

    # User interaction tracking
    is_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    is_clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    is_saved = models.BooleanField(default=False)
    saved_at = models.DateTimeField(null=True, blank=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    is_applied = models.BooleanField(default=False)  # For opportunity recommendations
    applied_at = models.DateTimeField(null=True, blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recommendations'
        ordering = ['user', '-relevance_score', 'rank']
        indexes = [
            models.Index(fields=['user', 'rec_type', '-relevance_score']),
            models.Index(fields=['user', 'is_dismissed', '-created_at']),
            models.Index(fields=['target_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.rec_type} recommendation for {self.user.email}: {self.relevance_score:.1f}"


class SearchIndex(models.Model):
    """Search index for fast talent/opportunity matching and discovery."""

    class EntityType(models.TextChoices):
        TALENT = 'talent', 'Talent'
        OPPORTUNITY = 'opportunity', 'Opportunity'
        ORGANIZATION = 'organization', 'Organization'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Entity being indexed
    entity_type = models.CharField(
        max_length=50,
        choices=EntityType.choices,
        db_index=True
    )
    entity_id = models.UUIDField(db_index=True)

    # Full-text search data
    search_text = models.TextField(blank=True)  # Combined searchable text
    keywords = models.JSONField(default=list, blank=True)  # Extracted keywords

    # Structured search fields
    skills = models.JSONField(default=list, blank=True)  # Skill IDs or names
    location_data = models.JSONField(default=dict, blank=True)  # Country, city, coordinates
    experience_level = models.CharField(max_length=50, blank=True)
    job_types = models.JSONField(default=list, blank=True)

    # Salary/compensation range
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, blank=True)

    # Vector embedding for semantic search
    embedding = models.JSONField(default=list, blank=True)  # 768-dimensional vector (or other)
    embedding_model = models.CharField(max_length=50, blank=True)

    # Boost factors for ranking
    boost_score = models.FloatField(default=1.0)  # Ranking multiplier
    quality_score = models.FloatField(default=0.0)  # Profile/posting quality

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)

    # Indexing metadata
    last_indexed = models.DateTimeField(auto_now=True)
    index_version = models.CharField(max_length=20, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'search_index'
        unique_together = ['entity_type', 'entity_id']
        indexes = [
            models.Index(fields=['entity_type', 'is_active']),
            models.Index(fields=['is_active', '-boost_score']),
            models.Index(fields=['-last_indexed']),
        ]

    def __str__(self):
        return f"{self.entity_type} index for {self.entity_id}"


class MatchHistory(models.Model):
    """Historical record of matches and their outcomes."""

    class Outcome(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        VIEWED = 'viewed', 'Viewed Only'
        DISMISSED = 'dismissed', 'Dismissed'
        SAVED = 'saved', 'Saved'
        NO_ACTION = 'no_action', 'No Action'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    match_score = models.ForeignKey(MatchScore, on_delete=models.CASCADE, related_name='history')

    # User action
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.NO_ACTION)

    # Feedback
    user_feedback = models.TextField(blank=True)
    feedback_score = models.IntegerField(null=True, blank=True)  # 1-5 stars

    # Timestamps
    outcome_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'match_history'
        ordering = ['-outcome_at']
        indexes = [
            models.Index(fields=['match_score', '-outcome_at']),
            models.Index(fields=['outcome']),
        ]

    def __str__(self):
        return f"Match {self.match_score.id}: {self.outcome}"

