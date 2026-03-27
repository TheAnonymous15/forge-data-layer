# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Application Serializers
======================================================
"""
from rest_framework import serializers
from .models import Application, ApplicationStatusHistory, Interview


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for application status history."""
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            'id', 'application', 'from_status', 'to_status',
            'changed_by', 'changed_by_email', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InterviewSerializer(serializers.ModelSerializer):
    """Serializer for interviews."""
    interviewer_emails = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = [
            'id', 'application', 'interview_type', 'status',
            'scheduled_at', 'duration_minutes', 'timezone',
            'location', 'meeting_link', 'interviewers', 'interviewer_emails',
            'notes', 'feedback', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_interviewer_emails(self, obj):
        return [i.email for i in obj.interviewers.all()]


class ApplicationSerializer(serializers.ModelSerializer):
    """Full serializer for applications."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    organization_name = serializers.CharField(source='opportunity.organization.name', read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'user', 'user_email', 'user_name', 'opportunity',
            'opportunity_title', 'organization_name', 'status',
            'cover_letter', 'resume_url', 'portfolio_url', 'answers',
            'applicant_notes', 'recruiter_notes', 'rating', 'match_score',
            'submitted_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_email',
            'status_history', 'interviews', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None


class ApplicationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for application lists."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    organization_name = serializers.CharField(source='opportunity.organization.name', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'user', 'user_email', 'opportunity', 'opportunity_title',
            'organization_name', 'status', 'rating', 'match_score',
            'submitted_at', 'created_at'
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating applications."""

    class Meta:
        model = Application
        fields = [
            'user', 'opportunity', 'cover_letter', 'resume_url',
            'portfolio_url', 'answers', 'applicant_notes'
        ]

    def validate(self, data):
        # Check if application already exists
        if Application.objects.filter(
            user=data['user'],
            opportunity=data['opportunity']
        ).exists():
            raise serializers.ValidationError(
                "You have already applied to this opportunity."
            )
        return data


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating applications."""

    class Meta:
        model = Application
        fields = [
            'status', 'cover_letter', 'resume_url', 'portfolio_url',
            'answers', 'applicant_notes', 'recruiter_notes',
            'rating', 'match_score'
        ]


class InterviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for scheduling interviews."""

    class Meta:
        model = Interview
        fields = [
            'application', 'interview_type', 'scheduled_at',
            'duration_minutes', 'timezone', 'location', 'meeting_link',
            'interviewers', 'notes'
        ]


class InterviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating interviews."""

    class Meta:
        model = Interview
        fields = [
            'status', 'scheduled_at', 'duration_minutes', 'timezone',
            'location', 'meeting_link', 'interviewers', 'notes', 'feedback'
        ]

