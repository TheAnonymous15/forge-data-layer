 # -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Analytics Models
===============================================
Platform analytics, event tracking, metrics, and reporting.
"""
import uuid
from django.db import models
from django.conf import settings


class PageView(models.Model):
    """Track page views for analytics."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_views'
    )

    # Page info
    page_path = models.CharField(max_length=500)
    page_title = models.CharField(max_length=200, blank=True)
    referrer = models.URLField(blank=True, max_length=1000)
    query_params = models.JSONField(default=dict, blank=True)

    # Session and device info
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # desktop, mobile, tablet
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)

    # Engagement
    duration_seconds = models.PositiveIntegerField(default=0)
    scroll_depth = models.PositiveIntegerField(default=0)  # Percentage

    # Location
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'analytics_page_views'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['page_path', '-created_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.page_path} - {self.created_at}"


class UserEvent(models.Model):
    """Track user events and interactions for analytics."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )

    # Event details
    event_type = models.CharField(max_length=100, db_index=True)  # button_click, form_submit, etc.
    event_category = models.CharField(max_length=100, blank=True)  # engagement, navigation, conversion
    event_label = models.CharField(max_length=200, blank=True)
    event_value = models.FloatField(null=True, blank=True)

    # Additional properties
    properties = models.JSONField(default=dict, blank=True)

    # Context
    page_path = models.CharField(max_length=500, blank=True)
    session_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Device info
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'analytics_user_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['event_category', '-created_at']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_label}"


class PlatformMetricSnapshot(models.Model):
    """Daily snapshot of platform-wide metrics."""

    class MetricType(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Snapshot info
    snapshot_date = models.DateField(db_index=True)
    metric_type = models.CharField(max_length=100, choices=MetricType.choices, default=MetricType.DAILY)

    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    verified_users = models.PositiveIntegerField(default=0)

    # Opportunity metrics
    total_opportunities = models.PositiveIntegerField(default=0)
    active_opportunities = models.PositiveIntegerField(default=0)
    new_opportunities = models.PositiveIntegerField(default=0)
    filled_opportunities = models.PositiveIntegerField(default=0)

    # Application metrics
    total_applications = models.PositiveIntegerField(default=0)
    new_applications = models.PositiveIntegerField(default=0)
    accepted_applications = models.PositiveIntegerField(default=0)
    rejected_applications = models.PositiveIntegerField(default=0)

    # Engagement metrics
    total_logins = models.PositiveIntegerField(default=0)
    total_page_views = models.PositiveIntegerField(default=0)
    avg_session_duration = models.FloatField(default=0.0)

    # Detailed metrics data
    metrics_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_metric_snapshots'
        unique_together = ['snapshot_date', 'metric_type']
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['-snapshot_date']),
            models.Index(fields=['metric_type', '-snapshot_date']),
        ]

    def __str__(self):
        return f"{self.metric_type} - {self.snapshot_date}"


class Report(models.Model):
    """Generated reports for analytics and business intelligence."""

    class ReportType(models.TextChoices):
        USER_ACTIVITY = 'user_activity', 'User Activity'
        APPLICATION_STATS = 'application_stats', 'Application Statistics'
        OPPORTUNITY_PERFORMANCE = 'opportunity_performance', 'Opportunity Performance'
        REVENUE = 'revenue', 'Revenue'
        CUSTOM = 'custom', 'Custom Report'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        GENERATING = 'generating', 'Generating'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class Format(models.TextChoices):
        PDF = 'pdf', 'PDF'
        CSV = 'csv', 'CSV'
        EXCEL = 'excel', 'Excel'
        JSON = 'json', 'JSON'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reports'
    )

    # Report details
    report_type = models.CharField(max_length=100, choices=ReportType.choices, default=ReportType.CUSTOM)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Parameters and filters
    parameters = models.JSONField(default=dict, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)

    # Report data
    data = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    # Output
    format = models.CharField(max_length=20, choices=Format.choices, default=Format.PDF)
    file_url = models.URLField(blank=True)
    file_size = models.PositiveIntegerField(default=0)  # bytes

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)

    # Timestamps
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['report_type', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.status}"

