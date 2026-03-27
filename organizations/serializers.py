# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Organization Serializers
=======================================================
"""
from rest_framework import serializers
from .models import Organization, OrganizationMember, OrganizationLocation


class OrganizationLocationSerializer(serializers.ModelSerializer):
    """Serializer for organization locations."""

    class Meta:
        model = OrganizationLocation
        fields = [
            'id', 'organization', 'name', 'country', 'city',
            'address', 'is_headquarters', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Serializer for organization members."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'organization_name', 'user', 'user_email',
            'user_name', 'role', 'title', 'is_active', 'invited_by',
            'invited_by_email', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing organizations."""
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'tagline', 'org_type', 'size',
            'industry', 'logo_url', 'headquarters_country', 'headquarters_city',
            'verification_status', 'is_active', 'is_featured',
            'total_opportunities', 'owner', 'owner_email', 'member_count',
            'created_at'
        ]

    def get_member_count(self, obj):
        return obj.members.count() if hasattr(obj, 'members') else 0


class OrganizationSerializer(serializers.ModelSerializer):
    """Full serializer for organization details."""
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_name = serializers.SerializerMethodField()
    members = OrganizationMemberSerializer(many=True, read_only=True)
    locations = OrganizationLocationSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    location_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'tagline',
            'org_type', 'size', 'industry', 'industry_other', 'founded_year',
            'email', 'phone', 'website',
            'headquarters_country', 'headquarters_city', 'headquarters_address',
            'linkedin_url', 'twitter_url', 'facebook_url',
            'logo_url', 'cover_image_url',
            'interest_types', 'initial_message', 'referral_source',
            'verification_status', 'is_active', 'is_featured',
            'total_opportunities', 'total_hires',
            'owner', 'owner_email', 'owner_name',
            'members', 'locations', 'member_count', 'location_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.email
        return None

    def get_member_count(self, obj):
        return obj.members.count() if hasattr(obj, 'members') else 0

    def get_location_count(self, obj):
        return obj.locations.count() if hasattr(obj, 'locations') else 0


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating organizations (from registration modal)."""
    
    # Extra fields from registration that go to the user, not organization
    contact_first_name = serializers.CharField(write_only=True, required=False)
    contact_last_name = serializers.CharField(write_only=True, required=False)
    contact_job_title = serializers.CharField(write_only=True, required=False)
    contact_email = serializers.EmailField(write_only=True, required=False)
    contact_phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'tagline', 'org_type', 'size',
            'industry', 'industry_other', 'founded_year', 
            'email', 'phone', 'website',
            'headquarters_country', 'headquarters_city', 'headquarters_address',
            'linkedin_url', 'twitter_url', 'facebook_url',
            'logo_url', 'cover_image_url', 'owner',
            'interest_types', 'initial_message', 'referral_source',
            # Contact person fields (write-only, handled in view)
            'contact_first_name', 'contact_last_name', 'contact_job_title',
            'contact_email', 'contact_phone',
        ]

    def validate_name(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Organization name must be at least 2 characters.")
        return value


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating organizations."""

    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'tagline', 'org_type', 'size',
            'industry', 'industry_other', 'founded_year', 
            'email', 'phone', 'website',
            'headquarters_country', 'headquarters_city', 'headquarters_address',
            'linkedin_url', 'twitter_url', 'facebook_url',
            'logo_url', 'cover_image_url', 
            'interest_types', 'initial_message', 'referral_source',
            'is_active', 'is_featured'
        ]
