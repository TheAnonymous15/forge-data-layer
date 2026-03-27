# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Analytics Serializers
====================================================
"""
from rest_framework import serializers
from .models import PageView, UserEvent, PlatformMetricSnapshot, Report


class PageViewSerializer(serializers.ModelSerializer):
    """Serializer for page views."""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = PageView
        fields = [
            'id', 'user', 'user_email', 'page_path', 'page_title',
            'referrer', 'query_params', 'session_id', 'user_agent',
            'ip_address', 'device_type', 'browser', 'os',
            'duration_seconds', 'scroll_depth', 'country', 'city',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PageViewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating page views (tracking)."""

    class Meta:
        model = PageView
        fields = [
            'page_path', 'page_title', 'referrer', 'query_params',
            'session_id', 'user_agent', 'ip_address', 'device_type',
            'browser', 'os', 'duration_seconds', 'scroll_depth',
            'country', 'city'
        ]


class UserEventSerializer(serializers.ModelSerializer):
    """Serializer for user events."""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserEvent
        fields = [
            'id', 'user', 'user_email', 'event_type', 'event_category',
            'event_label', 'event_value', 'properties', 'page_path',
            'session_id', 'user_agent', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserEventCreateSerializer(serializers.ModelSerializer):
    """Serializer for tracking user events."""

    class Meta:
        model = UserEvent
        fields = [
            'event_type', 'event_category', 'event_label', 'event_value',
            'properties', 'page_path', 'session_id'
        ]


class PlatformMetricSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for platform metric snapshots."""

    class Meta:
        model = PlatformMetricSnapshot
        fields = [
            'id', 'snapshot_date', 'metric_type',
            'total_users', 'active_users', 'new_users', 'verified_users',
            'total_opportunities', 'active_opportunities', 'new_opportunities', 'filled_opportunities',
            'total_applications', 'new_applications', 'accepted_applications', 'rejected_applications',
            'total_logins', 'total_page_views', 'avg_session_duration',
            'metrics_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for reports."""
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'created_by', 'created_by_email', 'report_type', 'title',
            'description', 'parameters', 'date_from', 'date_to',
            'data', 'summary', 'format', 'file_url', 'file_size',
            'status', 'error_message', 'generated_at', 'expires_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'data', 'summary', 'file_url', 'file_size',
            'status', 'error_message', 'generated_at', 'created_at', 'updated_at'
        ]


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports."""

    class Meta:
        model = Report
        fields = [
            'report_type', 'title', 'description', 'parameters',
            'date_from', 'date_to', 'format'
        ]


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report lists."""
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'created_by_email', 'report_type', 'title',
            'format', 'status', 'generated_at', 'created_at'
        ]

