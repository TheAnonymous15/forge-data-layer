# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer User Serializers
================================================
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for list views."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number',
            'role', 'is_active', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'date_of_birth', 'gender', 'country', 'city',
            'role', 'is_active', 'is_verified', 'two_factor_enabled',
            'metadata', 'terms_accepted_at', 'privacy_accepted_at',
            'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'last_login', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    terms_accepted = serializers.BooleanField(write_only=True)
    privacy_accepted = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'confirm_password', 'first_name', 'last_name',
            'phone_number', 'date_of_birth', 'gender', 'country', 'city',
            'role', 'metadata', 'terms_accepted', 'privacy_accepted'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match'})

        if not attrs.pop('terms_accepted', False):
            raise serializers.ValidationError({'terms_accepted': 'You must accept the terms of service'})

        if not attrs.pop('privacy_accepted', False):
            raise serializers.ValidationError({'privacy_accepted': 'You must accept the privacy policy'})

        return attrs

    def create(self, validated_data):
        from django.utils import timezone

        password = validated_data.pop('password')
        validated_data['terms_accepted_at'] = timezone.now()
        validated_data['privacy_accepted_at'] = timezone.now()

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user data."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number',
            'date_of_birth', 'gender', 'country', 'city', 'metadata'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password."""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match'})
        return attrs


class LoginSerializer(serializers.Serializer):
    """Serializer for login requests."""
    email = serializers.EmailField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(default=False)
    device_info = serializers.JSONField(required=False)


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification."""
    token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password."""
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset."""
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match'})
        return attrs

