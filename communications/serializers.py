# -*- coding: utf-8 -*-
"""
Communications Serializers
==========================
"""
from rest_framework import serializers
from .models import Notification, EmailLog, Message, Announcement


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notif_type', 'channel', 'title', 'body',
            'action_url', 'data', 'ref_type', 'ref_id',
            'is_read', 'read_at', 'status', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = [
            'id', 'recipient_email', 'subject', 'template_name',
            'status', 'error_message',
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    sender_name = serializers.SerializerMethodField()
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_email', 'sender_name',
            'recipient', 'recipient_email', 'recipient_name',
            'subject', 'body', 'parent', 'thread_id',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'thread_id', 'created_at']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.email

    def get_recipient_name(self, obj):
        return f"{obj.recipient.first_name} {obj.recipient.last_name}".strip() or obj.recipient.email


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'target_roles',
            'is_active', 'is_pinned', 'start_date', 'end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

