# -*- coding: utf-8 -*-
"""Analytics API Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PageView, UserEvent, PlatformMetricSnapshot, Report
from .serializers import PageViewSerializer, UserEventSerializer, PlatformMetricSnapshotSerializer, ReportSerializer


class PageViewViewSet(viewsets.ModelViewSet):
    """API endpoint for page views."""
    serializer_class = PageViewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PageView.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track a page view."""
        data = request.data.copy()
        data['ip_address'] = request.META.get('REMOTE_ADDR')
        data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

        serializer = PageViewSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user if request.user.is_authenticated else None)
            return Response({'success': True})
        return Response({'success': False, 'errors': serializer.errors}, status=400)


class UserEventViewSet(viewsets.ModelViewSet):
    """API endpoint for user events."""
    serializer_class = UserEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserEvent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track a user event."""
        serializer = UserEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user if request.user.is_authenticated else None)
            return Response({'success': True})
        return Response({'success': False, 'errors': serializer.errors}, status=400)


class PlatformMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for platform metrics."""
    queryset = PlatformMetricSnapshot.objects.all()
    serializer_class = PlatformMetricSnapshotSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest metrics."""
        from django.utils import timezone
        today = timezone.now().date()
        metrics = self.queryset.filter(snapshot_date=today)
        return Response({
            'success': True,
            'data': PlatformMetricSnapshotSerializer(metrics, many=True).data
        })


class ReportViewSet(viewsets.ModelViewSet):
    """API endpoint for reports."""
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, status='generating')

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate a report."""
        report = self.get_object()
        report.status = 'generating'
        report.save()
        # Trigger async report generation
        return Response({'success': True, 'message': 'Report regeneration started'})

