# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Application Models
=================================================
Job application tracking and workflow.
"""
import uuid
from django.db import models
from django.conf import settings


class Application(models.Model):
    """Job application model."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        INTERVIEW = 'interview', 'Interview Scheduled'
        ASSESSMENT = 'assessment', 'Assessment'
        OFFER = 'offer', 'Offer Extended'
        ACCEPTED = 'accepted', 'Offer Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    opportunity = models.ForeignKey(
        'opportunities.Opportunity',
        on_delete=models.CASCADE,
        related_name='applications'
    )

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    # Application Data
    cover_letter = models.TextField(null=True, blank=True)
    resume_url = models.URLField(null=True, blank=True)
    portfolio_url = models.URLField(null=True, blank=True)
    answers = models.JSONField(default=dict, blank=True)  # Custom question answers

    # Notes
    applicant_notes = models.TextField(null=True, blank=True)
    recruiter_notes = models.TextField(null=True, blank=True)

    # Ratings
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'applications'
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        unique_together = ['user', 'opportunity']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['opportunity', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.opportunity.title}"


class ApplicationStatusHistory(models.Model):
    """Track application status changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'application_status_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.id}: {self.from_status} -> {self.to_status}"


class Interview(models.Model):
    """Interview scheduling."""

    class InterviewType(models.TextChoices):
        PHONE = 'phone', 'Phone Screen'
        VIDEO = 'video', 'Video Call'
        ONSITE = 'onsite', 'On-site'
        TECHNICAL = 'technical', 'Technical Interview'
        PANEL = 'panel', 'Panel Interview'
        FINAL = 'final', 'Final Interview'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'
        RESCHEDULED = 'rescheduled', 'Rescheduled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')

    interview_type = models.CharField(max_length=20, choices=InterviewType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    timezone = models.CharField(max_length=50, default='Africa/Johannesburg')

    location = models.CharField(max_length=500, null=True, blank=True)  # Physical or virtual link
    meeting_link = models.URLField(null=True, blank=True)

    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='interviews_conducted',
        blank=True
    )

    notes = models.TextField(null=True, blank=True)
    feedback = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'interviews'
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.application.user.email} - {self.interview_type} at {self.scheduled_at}"

