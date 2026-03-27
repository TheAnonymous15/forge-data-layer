# -*- coding: utf-8 -*-
"""Security API Views."""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import APIKey, SecurityEvent, ConsentRecord, BlockedIP
from .serializers import APIKeySerializer, SecurityEventSerializer, ConsentRecordSerializer, BlockedIPSerializer


class APIKeyViewSet(viewsets.ModelViewSet):
    """API endpoint for API keys."""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return APIKey.objects.all()
        return APIKey.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke an API key."""
        key = self.get_object()
        key.is_active = False
        key.save()
        return Response({'success': True, 'message': 'API key revoked'})


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for security events."""
    queryset = SecurityEvent.objects.all()
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark event as resolved."""
        event = self.get_object()
        from django.utils import timezone
        event.is_resolved = True
        event.resolved_at = timezone.now()
        event.resolution_notes = request.data.get('notes', '')
        event.save()
        return Response({'success': True})


class ConsentRecordViewSet(viewsets.ModelViewSet):
    """API endpoint for consent records."""
    serializer_class = ConsentRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConsentRecord.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def grant(self, request):
        """Grant consent."""
        from django.utils import timezone
        consent_type = request.data.get('consent_type')
        version = request.data.get('version', '1.0')

        record, created = ConsentRecord.objects.update_or_create(
            user=request.user,
            consent_type=consent_type,
            defaults={
                'version': version,
                'is_granted': True,
                'granted_at': timezone.now(),
                'withdrawn_at': None,
                'ip_address': request.META.get('REMOTE_ADDR')
            }
        )
        return Response({'success': True, 'data': ConsentRecordSerializer(record).data})

    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdraw consent."""
        from django.utils import timezone
        consent_type = request.data.get('consent_type')

        try:
            record = ConsentRecord.objects.get(user=request.user, consent_type=consent_type, is_granted=True)
            record.is_granted = False
            record.withdrawn_at = timezone.now()
            record.save()
            return Response({'success': True})
        except ConsentRecord.DoesNotExist:
            return Response({'success': False, 'error': 'No active consent found'}, status=404)


class BlockedIPViewSet(viewsets.ModelViewSet):
    """API endpoint for blocked IPs."""
    queryset = BlockedIP.objects.all()
    serializer_class = BlockedIPSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if an IP is blocked."""
        ip = request.query_params.get('ip')
        if not ip:
            return Response({'success': False, 'error': 'ip required'}, status=400)

        from django.utils import timezone
        blocked = BlockedIP.objects.filter(
            ip_address=ip
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).exists()

        return Response({'success': True, 'blocked': blocked})

