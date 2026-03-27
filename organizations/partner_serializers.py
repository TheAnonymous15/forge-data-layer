# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Partner User Serializers
=============================================
Serializers for partner/employer authentication and management.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from .partner_models import (
    PartnerUser, PartnerSession, PartnerLoginHistory,
    PartnerEmailVerificationToken, PartnerPasswordResetToken
)
from .models import Organization


class PartnerUserSerializer(serializers.ModelSerializer):
    """Serializer for PartnerUser model."""
    
    full_name = serializers.ReadOnlyField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = PartnerUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_code', 'phone_number', 'organization', 'organization_name',
            'role', 'job_title', 'department',
            'can_post_opportunities', 'can_manage_applications',
            'can_manage_team', 'can_manage_settings', 'can_view_analytics',
            'is_active', 'is_verified', 'is_primary_contact',
            'two_factor_enabled', 'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class PartnerUserResponseSerializer(serializers.ModelSerializer):
    """Serializer for partner user response (safe data only)."""
    
    full_name = serializers.ReadOnlyField()
    organization_id = serializers.UUIDField(source='organization.id', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = PartnerUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_code', 'phone_number',
            'organization_id', 'organization_name',
            'role', 'job_title', 'department',
            'is_active', 'is_verified', 'is_primary_contact',
            'two_factor_enabled', 'last_login', 'created_at'
        ]
        read_only_fields = fields


class PartnerRegisterSerializer(serializers.Serializer):
    """
    Serializer for partner/organization registration.
    Creates both Organization and PartnerUser.
    """
    
    # ═══════════════════════════════════════════════════════════════
    # CONTACT PERSON FIELDS (Required)
    # ═══════════════════════════════════════════════════════════════
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    job_title = serializers.CharField(required=True, max_length=100)
    phone_code = serializers.CharField(required=False, allow_blank=True, max_length=10)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    
    # ═══════════════════════════════════════════════════════════════
    # ORGANIZATION FIELDS (Required)
    # ═══════════════════════════════════════════════════════════════
    organization_name = serializers.CharField(required=True, max_length=200)
    organization_industry = serializers.ChoiceField(
        choices=[
            ('technology', 'Technology'),
            ('finance', 'Finance & Banking'),
            ('healthcare', 'Healthcare'),
            ('education', 'Education'),
            ('manufacturing', 'Manufacturing'),
            ('consulting', 'Consulting'),
            ('retail', 'Retail & E-commerce'),
            ('media', 'Media & Entertainment'),
            ('agriculture', 'Agriculture'),
            ('energy', 'Energy & Utilities'),
            ('transportation', 'Transportation'),
            ('hospitality', 'Hospitality'),
            ('legal', 'Legal Services'),
            ('ngo', 'NGO / Non-Profit'),
            ('government', 'Government'),
            ('other', 'Other'),
        ],
        required=True
    )
    organization_industry_other = serializers.CharField(required=False, allow_blank=True, max_length=100)
    organization_size = serializers.ChoiceField(
        choices=[
            ('1', '1 employee'),
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-500', '201-500 employees'),
            ('500+', '500+ employees'),
        ],
        required=True
    )
    organization_website = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    organization_country = serializers.CharField(required=True, max_length=100)
    
    # Interest/Looking for
    organization_interest_types = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('hire_talent', 'Hire Talent'),
            ('internships', 'Offer Internships'),
            ('volunteer', 'Volunteer Programs'),
            ('partnership', 'Partnership'),
            ('mentorship', 'Mentorship'),
            ('sponsorship', 'Sponsorship'),
        ]),
        required=False,
        default=list
    )
    
    # Initial message/needs
    organization_message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    
    # ═══════════════════════════════════════════════════════════════
    # CONSENT FIELDS (Required)
    # ═══════════════════════════════════════════════════════════════
    consent_terms = serializers.BooleanField(required=True)
    consent_data = serializers.BooleanField(required=True)
    consent_authorized = serializers.BooleanField(required=True)
    
    # Metadata
    ip_address = serializers.IPAddressField(required=False, allow_blank=True, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_email(self, value):
        """Check email is unique in partner_users table."""
        if PartnerUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A partner with this email already exists.")
        return value.lower()
    
    def validate_phone(self, value):
        """Check phone number format if provided."""
        if value:
            cleaned = ''.join(c for c in value if c.isdigit())
            if len(cleaned) < 6 or len(cleaned) > 15:
                raise serializers.ValidationError("Phone number must be 6-15 digits.")
        return value
    
    def validate(self, data):
        """Validate partner registration data."""
        # Passwords must match
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Validate password strength
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        # All consent fields are required for partners
        if not data.get('consent_terms'):
            raise serializers.ValidationError({"consent_terms": "You must accept the terms of service."})
        
        if not data.get('consent_data'):
            raise serializers.ValidationError({"consent_data": "You must accept the privacy policy."})
        
        if not data.get('consent_authorized'):
            raise serializers.ValidationError({
                "consent_authorized": "You must confirm you are authorized to register on behalf of this organization."
            })
        
        # If industry is 'other', require industry_other
        if data.get('organization_industry') == 'other' and not data.get('organization_industry_other'):
            raise serializers.ValidationError({
                "organization_industry_other": "Please specify the industry when selecting 'Other'."
            })
        
        # Check phone uniqueness if provided
        phone_code = data.get('phone_code', '').strip()
        phone = data.get('phone', '').strip()
        if phone_code and phone:
            phone_number = f"{phone_code}{phone}"
            if PartnerUser.objects.filter(phone_number=phone_number).exists():
                raise serializers.ValidationError({"phone": "A partner with this phone number already exists."})
        
        return data


class PartnerLoginSerializer(serializers.Serializer):
    """Serializer for partner login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    # Metadata
    ip_address = serializers.IPAddressField(required=False, allow_blank=True, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PartnerPasswordChangeSerializer(serializers.Serializer):
    """Serializer for partner password change."""
    
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        try:
            validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return data


class PartnerEmailVerificationSerializer(serializers.Serializer):
    """Serializer for partner email verification."""
    token = serializers.CharField(required=True)


class PartnerPasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for partner password reset request."""
    email = serializers.EmailField(required=True)


class PartnerPasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for partner password reset confirmation."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        try:
            validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return data

