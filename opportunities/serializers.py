# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Opportunity Serializers
=====================================================
"""
from rest_framework import serializers
from .models import Opportunity, SavedOpportunity


class OpportunitySerializer(serializers.ModelSerializer):
    """Full Opportunity Serializer."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_logo = serializers.CharField(source='organization.logo_url', read_only=True)
    posted_by_email = serializers.CharField(source='posted_by.email', read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'slug', 'summary', 'description', 'organization',
            'organization_name', 'organization_logo', 'posted_by', 'posted_by_email',
            'opportunity_type', 'experience_level', 'category', 'location',
            'country', 'city', 'remote_policy', 'salary_min', 'salary_max',
            'salary_currency', 'salary_period', 'hide_salary', 'benefits',
            'requirements', 'qualifications', 'responsibilities',
            'required_skills', 'preferred_skills', 'min_experience_years',
            'positions_available', 'external_apply_url', 'status',
            'is_featured', 'is_urgent', 'start_date', 'deadline',
            'published_at', 'views_count', 'applications_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'views_count', 'applications_count', 'created_at', 'updated_at']


class OpportunityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for opportunity lists."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_logo = serializers.CharField(source='organization.logo_url', read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'slug', 'summary', 'organization', 'organization_name',
            'organization_logo', 'opportunity_type', 'experience_level', 'category',
            'location', 'country', 'city', 'remote_policy', 'salary_min',
            'salary_max', 'salary_currency', 'hide_salary', 'status',
            'is_featured', 'is_urgent', 'deadline', 'published_at',
            'views_count', 'applications_count', 'created_at'
        ]


class OpportunityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating opportunities."""

    class Meta:
        model = Opportunity
        fields = [
            'title', 'summary', 'description', 'organization', 'posted_by',
            'opportunity_type', 'experience_level', 'category', 'location',
            'country', 'city', 'remote_policy', 'salary_min', 'salary_max',
            'salary_currency', 'salary_period', 'hide_salary', 'benefits',
            'requirements', 'qualifications', 'responsibilities',
            'required_skills', 'preferred_skills', 'min_experience_years',
            'positions_available', 'external_apply_url', 'start_date', 'deadline'
        ]


class SavedOpportunitySerializer(serializers.ModelSerializer):
    """Serializer for saved opportunities."""
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    opportunity_slug = serializers.CharField(source='opportunity.slug', read_only=True)
    organization_name = serializers.CharField(source='opportunity.organization.name', read_only=True)

    class Meta:
        model = SavedOpportunity
        fields = [
            'id', 'user', 'opportunity', 'opportunity_title', 'opportunity_slug',
            'organization_name', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

