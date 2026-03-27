# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Profile Serializers
===================================================
"""
from rest_framework import serializers
from .models import (
    TalentProfile, Skill, TalentSkill, Education,
    WorkExperience, Certification, Language
)


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skills."""

    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'slug', 'category', 'description',
            'parent', 'is_verified', 'usage_count', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'usage_count', 'created_at']


class TalentSkillSerializer(serializers.ModelSerializer):
    """Serializer for TalentSkill associations."""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_category = serializers.CharField(source='skill.category', read_only=True)

    class Meta:
        model = TalentSkill
        fields = [
            'id', 'profile', 'skill', 'skill_name', 'skill_category',
            'proficiency', 'years_of_experience', 'is_primary',
            'endorsements_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'endorsements_count', 'created_at', 'updated_at']


class EducationSerializer(serializers.ModelSerializer):
    """Serializer for Education records."""

    class Meta:
        model = Education
        fields = [
            'id', 'profile', 'institution', 'degree_type', 'field_of_study',
            'start_date', 'end_date', 'is_current', 'grade', 'description',
            'location', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkExperienceSerializer(serializers.ModelSerializer):
    """Serializer for Work Experience records."""

    class Meta:
        model = WorkExperience
        fields = [
            'id', 'profile', 'company', 'title', 'employment_type',
            'location', 'is_remote', 'start_date', 'end_date', 'is_current',
            'description', 'achievements', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CertificationSerializer(serializers.ModelSerializer):
    """Serializer for Certifications."""

    class Meta:
        model = Certification
        fields = [
            'id', 'profile', 'name', 'issuing_organization', 'issue_date',
            'expiry_date', 'credential_id', 'credential_url', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LanguageSerializer(serializers.ModelSerializer):
    """Serializer for Language proficiencies."""

    class Meta:
        model = Language
        fields = [
            'id', 'profile', 'language', 'proficiency', 'is_native',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TalentProfileSerializer(serializers.ModelSerializer):
    """Serializer for Talent Profile."""
    skills = TalentSkillSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    work_experience = WorkExperienceSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = TalentProfile
        fields = [
            'id', 'user', 'user_email', 'user_name', 'headline', 'bio',
            'experience_level', 'availability_status', 'available_from',
            'preferred_job_types', 'preferred_locations', 'remote_preference',
            'salary_expectation_min', 'salary_expectation_max', 'salary_currency',
            'linkedin_url', 'github_url', 'portfolio_url', 'website_url',
            'profile_completeness', 'profile_score', 'is_public',
            'show_email', 'show_phone', 'skills', 'education',
            'work_experience', 'certifications', 'languages',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'profile_completeness', 'profile_score', 'created_at', 'updated_at']


class TalentProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for profile lists."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    skills_count = serializers.IntegerField(source='skills.count', read_only=True)

    class Meta:
        model = TalentProfile
        fields = [
            'id', 'user', 'user_email', 'user_name', 'headline',
            'experience_level', 'availability_status', 'profile_completeness',
            'profile_score', 'is_public', 'skills_count', 'created_at'
        ]


class TalentProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating talent profiles."""

    class Meta:
        model = TalentProfile
        fields = [
            'headline', 'bio', 'experience_level', 'availability_status',
            'available_from', 'preferred_job_types', 'preferred_locations',
            'remote_preference', 'salary_expectation_min', 'salary_expectation_max',
            'salary_currency', 'linkedin_url', 'github_url', 'portfolio_url',
            'website_url', 'is_public', 'show_email', 'show_phone'
        ]

