# -*- coding: utf-8 -*-
"""Security Serializers."""
from rest_framework import serializers
from .models import APIKey, SecurityEvent, ConsentRecord, BlockedIP


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key_prefix', 'permissions', 'allowed_ips', 'rate_limit', 'is_active', 'expires_at', 'last_used_at', 'created_at']
        read_only_fields = ['id', 'key_prefix', 'created_at', 'last_used_at']


class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = '__all__'


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


class BlockedIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedIP
        fields = '__all__'

