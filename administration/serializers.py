# -*- coding: utf-8 -*-
"""Administration Serializers."""
from rest_framework import serializers
from .models import StaffRole, StaffRoleAssignment, FeatureFlag, AdminAuditLog, SupportTicket


class StaffRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffRole
        fields = '__all__'


class StaffRoleAssignmentSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = StaffRoleAssignment
        fields = '__all__'


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = '__all__'


class AdminAuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AdminAuditLog
        fields = '__all__'


class SupportTicketSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'resolved_at']

