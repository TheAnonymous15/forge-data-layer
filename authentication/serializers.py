# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Authentication Serializers
=========================================================
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration (Individual and Partner/Organization)."""
    
    # Required fields
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    
    # Phone
    phone_code = serializers.CharField(required=False, allow_blank=True, max_length=10)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    
    # Personal info
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=['male', 'female'],
        required=False, allow_blank=True, allow_null=True
    )
    bio = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    # Education
    education_level = serializers.ChoiceField(
        choices=['high_school', 'certificate', 'bachelors', 'masters', 'doctorate', 'self_taught', 'other'],
        required=False, allow_blank=True, allow_null=True
    )
    
    # Opportunity preferences (for talent)
    opportunity_types = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    
    # Skills and fields (for talent)
    skills = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    preferred_fields = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    
    # Referral
    referral_source = serializers.CharField(required=False, allow_blank=True, max_length=50)
    
    # Role (default to talent)
    role = serializers.ChoiceField(
        choices=['talent', 'employer', 'partner'],
        default='talent'
    )
    
    # Job title (for employer/partner)
    job_title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    
    # ═══════════════════════════════════════════════════════════════
    # ORGANIZATION FIELDS (for employer/partner registration)
    # ═══════════════════════════════════════════════════════════════
    organization_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    organization_industry = serializers.CharField(required=False, allow_blank=True, max_length=100)
    organization_industry_other = serializers.CharField(required=False, allow_blank=True, max_length=100)
    organization_size = serializers.CharField(required=False, allow_blank=True, max_length=20)
    organization_website = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    organization_country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    organization_interest_types = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )  # ['hire_talent', 'internships', 'volunteer', 'partnership']
    organization_message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    
    # ═══════════════════════════════════════════════════════════════
    # CONSENT FIELDS
    # ═══════════════════════════════════════════════════════════════
    consent_age = serializers.BooleanField(required=False, default=False)
    consent_data = serializers.BooleanField(required=False, default=False)
    consent_terms = serializers.BooleanField(required=False, default=False)
    consent_authorized = serializers.BooleanField(required=False, default=False)  # For partners
    
    # Legacy consent fields
    terms_accepted = serializers.BooleanField(required=False, default=False)
    privacy_accepted = serializers.BooleanField(required=False, default=False)
    marketing_consent = serializers.BooleanField(default=False)
    
    # Metadata
    ip_address = serializers.IPAddressField(required=False, allow_blank=True, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_email(self, value):
        """Check email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_phone(self, value):
        """Check phone number format if provided."""
        if value:
            # Remove spaces and dashes
            cleaned = ''.join(c for c in value if c.isdigit())
            if len(cleaned) < 6 or len(cleaned) > 15:
                raise serializers.ValidationError("Phone number must be 6-15 digits.")
        return value
    
    def validate(self, data):
        """Validate passwords match and meet requirements."""
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        # Accept either old or new consent field names
        terms_accepted = data.get('terms_accepted') or data.get('consent_terms', False)
        privacy_accepted = data.get('privacy_accepted') or data.get('consent_data', False)
        
        if not terms_accepted:
            raise serializers.ValidationError({"consent_terms": "You must accept the terms of service."})
        
        if not privacy_accepted:
            raise serializers.ValidationError({"consent_data": "You must accept the privacy policy."})
        
        # Validate password strength
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    ip_address = serializers.IPAddressField(required=False, allow_blank=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)


class LogoutSerializer(serializers.Serializer):
    """Serializer for user logout."""
    
    user_id = serializers.UUIDField(required=True)
    refresh_token = serializers.CharField(required=False, allow_blank=True)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password."""
    
    user_id = serializers.UUIDField(required=True)
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        try:
            validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""
    
    email = serializers.EmailField(required=True)
    ip_address = serializers.IPAddressField(required=False, allow_blank=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        
        try:
            validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return data


# =============================================================================
# Token Serializers
# =============================================================================

class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh."""
    refresh = serializers.CharField(required=True)


class TokenVerifySerializer(serializers.Serializer):
    """Serializer for token verification."""
    token = serializers.CharField(required=True)


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification."""
    token = serializers.CharField(required=True)


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification email."""
    email = serializers.EmailField(required=True)


class UserResponseSerializer(serializers.ModelSerializer):
    """Serializer for user response data."""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_code', 'phone_number', 'role', 'country', 'city',
            'date_of_birth', 'gender', 'bio', 'education_level',
            'opportunity_types', 'skills', 'preferred_fields',
            'referral_source', 'job_title', 'organization_id', 'consent_authorized',
            'is_active', 'is_verified', 'two_factor_enabled',
            'created_at', 'last_login'
        ]
        read_only_fields = fields


class PartnerRegisterSerializer(serializers.Serializer):
    """
    Serializer for partner/organization registration.
    
    This is a dedicated serializer for partners that requires organization
    details and validates partner-specific fields.
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
    consent_authorized = serializers.BooleanField(required=True)  # Authorized to act on behalf of organization
    
    # Metadata
    ip_address = serializers.IPAddressField(required=False, allow_blank=True, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_email(self, value):
        """Check email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
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
        
        return data

