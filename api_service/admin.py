# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import APIServiceUser, APIServiceAccessRequest, APIServiceAuditLog


@admin.register(APIServiceUser)
class APIServiceUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'status', 'last_login', 'created_at']
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['username', 'email', 'full_name', 'organization']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login', 'login_count']
    ordering = ['-created_at']


@admin.register(APIServiceAccessRequest)
class APIServiceAccessRequestAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'requested_role', 'status', 'created_at']
    list_filter = ['status', 'requested_role', 'created_at']
    search_fields = ['full_name', 'email', 'organization']
    readonly_fields = ['id', 'created_at', 'updated_at', 'reviewed_at']
    ordering = ['-created_at']


@admin.register(APIServiceAuditLog)
class APIServiceAuditLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'action', 'resource_type', 'ip_address', 'created_at']
    list_filter = ['action', 'resource_type', 'created_at']
    search_fields = ['username', 'action', 'resource_type']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']

