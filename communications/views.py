# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Communications Views
===================================================
Complete CRUD endpoints for notifications, messages, emails.
"""
import logging
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Notification, EmailLog, Message, Announcement
from .serializers import (
    NotificationSerializer, EmailLogSerializer,
    MessageSerializer, AnnouncementSerializer
)

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Notifications.

    Endpoints:
    - GET /notifications/ - List all notifications
    - POST /notifications/ - Create notification
    - GET /notifications/{id}/ - Get notification details
    - PUT/PATCH /notifications/{id}/ - Update notification
    - DELETE /notifications/{id}/ - Delete notification
    - POST /notifications/{id}/mark-read/ - Mark as read
    - POST /notifications/mark-all-read/ - Mark all as read
    - GET /notifications/unread-count/ - Get unread count
    - GET /notifications/by-user/ - Get notifications for user
    """
    queryset = Notification.objects.select_related('recipient')
    serializer_class = NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(recipient_id=user_id)

        notif_type = self.request.query_params.get('type')
        if notif_type:
            queryset = queryset.filter(notif_type=notif_type)

        channel = self.request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)

        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])

        return Response({
            'id': str(notification.id),
            'is_read': True,
            'message': 'Notification marked as read'
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for a user."""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        count = Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({
            'updated_count': count,
            'message': f'{count} notifications marked as read'
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        count = Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).count()

        return Response({'unread_count': count})

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get notifications for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        notifications = self.queryset.filter(recipient_id=user_id)[:50]
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)


class EmailLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Email Logs.

    Endpoints:
    - GET /email-logs/ - List all email logs
    - POST /email-logs/ - Create email log
    - GET /email-logs/{id}/ - Get email log details
    - GET /email-logs/by-recipient/ - Get emails for recipient
    """
    queryset = EmailLog.objects.select_related('recipient')
    serializer_class = EmailLogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        email_status = self.request.query_params.get('status')
        if email_status:
            queryset = queryset.filter(status=email_status)

        recipient_email = self.request.query_params.get('recipient_email')
        if recipient_email:
            queryset = queryset.filter(recipient_email=recipient_email)

        template_name = self.request.query_params.get('template_name')
        if template_name:
            queryset = queryset.filter(template_name=template_name)

        return queryset

    @action(detail=False, methods=['get'])
    def by_recipient(self, request):
        """Get email logs for a recipient."""
        email = request.query_params.get('email')
        if not email:
            return Response({'error': 'email is required'}, status=400)

        logs = self.queryset.filter(recipient_email=email)[:50]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Messages.

    Endpoints:
    - GET /messages/ - List all messages
    - POST /messages/ - Send message
    - GET /messages/{id}/ - Get message details
    - POST /messages/{id}/mark-read/ - Mark as read
    - GET /messages/conversations/ - Get conversations for user
    - GET /messages/thread/{thread_id}/ - Get message thread
    """
    queryset = Message.objects.select_related('sender', 'recipient')
    serializer_class = MessageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        sender_id = self.request.query_params.get('sender_id')
        if sender_id:
            queryset = queryset.filter(sender_id=sender_id)

        recipient_id = self.request.query_params.get('recipient_id')
        if recipient_id:
            queryset = queryset.filter(recipient_id=recipient_id)

        thread_id = self.request.query_params.get('thread_id')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)

        return queryset

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read."""
        message = self.get_object()
        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=['is_read', 'read_at'])

        return Response({
            'id': str(message.id),
            'is_read': True,
            'message': 'Message marked as read'
        })

    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """Get conversations for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        # Get unique conversation partners
        sent = Message.objects.filter(sender_id=user_id).values_list('recipient_id', flat=True)
        received = Message.objects.filter(recipient_id=user_id).values_list('sender_id', flat=True)

        partners = set(list(sent) + list(received))

        conversations = []
        for partner_id in partners:
            last_message = Message.objects.filter(
                Q(sender_id=user_id, recipient_id=partner_id) |
                Q(sender_id=partner_id, recipient_id=user_id)
            ).order_by('-created_at').first()

            if last_message:
                conversations.append({
                    'partner_id': str(partner_id),
                    'last_message': MessageSerializer(last_message).data,
                    'unread_count': Message.objects.filter(
                        sender_id=partner_id,
                        recipient_id=user_id,
                        is_read=False
                    ).count()
                })

        return Response(conversations)

    @action(detail=False, methods=['get'], url_path='thread/(?P<thread_id>[^/.]+)')
    def thread(self, request, thread_id=None):
        """Get all messages in a thread."""
        messages = self.queryset.filter(thread_id=thread_id).order_by('created_at')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Announcements.

    Endpoints:
    - GET /announcements/ - List all announcements
    - POST /announcements/ - Create announcement
    - GET /announcements/{id}/ - Get announcement details
    - PUT/PATCH /announcements/{id}/ - Update announcement
    - DELETE /announcements/{id}/ - Delete announcement
    - GET /announcements/active/ - Get active announcements
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        is_pinned = self.request.query_params.get('is_pinned')
        if is_pinned is not None:
            queryset = queryset.filter(is_pinned=is_pinned.lower() == 'true')

        return queryset

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active announcements."""
        now = timezone.now().date()
        announcements = self.queryset.filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by('-is_pinned', '-created_at')

        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)


# ============================================================
# Standalone API Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def communications_stats(request):
    """Get communications statistics."""
    return Response({
        'total_notifications': Notification.objects.count(),
        'unread_notifications': Notification.objects.filter(is_read=False).count(),
        'total_emails': EmailLog.objects.count(),
        'emails_sent': EmailLog.objects.filter(status='sent').count(),
        'emails_failed': EmailLog.objects.filter(status='failed').count(),
        'total_messages': Message.objects.count(),
        'unread_messages': Message.objects.filter(is_read=False).count(),
        'active_announcements': Announcement.objects.filter(is_active=True).count()
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def send_notification(request):
    """Send a notification to a user."""
    recipient_id = request.data.get('recipient_id')
    notif_type = request.data.get('type', 'system')
    channel = request.data.get('channel', 'in_app')
    title = request.data.get('title')
    body = request.data.get('body')
    action_url = request.data.get('action_url', '')
    data = request.data.get('data', {})

    if not all([recipient_id, title, body]):
        return Response({'error': 'recipient_id, title, and body are required'}, status=400)

    notification = Notification.objects.create(
        recipient_id=recipient_id,
        notif_type=notif_type,
        channel=channel,
        title=title,
        body=body,
        action_url=action_url,
        data=data,
        status='sent',
        sent_at=timezone.now()
    )

    return Response({
        'id': str(notification.id),
        'message': 'Notification sent successfully'
    })

