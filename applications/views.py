# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Application Views
================================================
Complete CRUD endpoints for applications and interviews.
"""
import logging
from django.utils import timezone
from django.db.models import F
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Application, ApplicationStatusHistory, Interview
from .serializers import (
    ApplicationSerializer, ApplicationListSerializer,
    ApplicationCreateSerializer, ApplicationStatusHistorySerializer,
    InterviewSerializer, InterviewCreateSerializer, InterviewUpdateSerializer
)

logger = logging.getLogger(__name__)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Applications.

    Endpoints:
    - GET /applications/ - List all applications
    - POST /applications/ - Create new application
    - GET /applications/{id}/ - Get application details
    - PUT/PATCH /applications/{id}/ - Update application
    - DELETE /applications/{id}/ - Delete application
    - POST /applications/{id}/submit/ - Submit application
    - POST /applications/{id}/update-status/ - Update status
    - POST /applications/{id}/withdraw/ - Withdraw application
    - GET /applications/by-user/ - Get applications by user
    - GET /applications/by-opportunity/ - Get applications by opportunity
    - GET /applications/by-organization/ - Get applications by organization
    """
    queryset = Application.objects.select_related(
        'user', 'opportunity', 'opportunity__organization', 'reviewed_by'
    ).prefetch_related('status_history', 'interviews')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return ApplicationListSerializer
        elif self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by opportunity
        opp_id = self.request.query_params.get('opportunity_id')
        if opp_id:
            queryset = queryset.filter(opportunity_id=opp_id)

        # Filter by organization
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(opportunity__organization_id=org_id)

        # Filter by status
        app_status = self.request.query_params.get('status')
        if app_status:
            queryset = queryset.filter(status=app_status)

        # Filter by multiple statuses
        statuses = self.request.query_params.get('statuses')
        if statuses:
            status_list = [s.strip() for s in statuses.split(',')]
            queryset = queryset.filter(status__in=status_list)

        return queryset

    def perform_create(self, serializer):
        application = serializer.save(status='submitted', submitted_at=timezone.now())

        # Update opportunity applications count
        application.opportunity.applications_count = F('applications_count') + 1
        application.opportunity.save(update_fields=['applications_count'])

        # Create status history
        ApplicationStatusHistory.objects.create(
            application=application,
            to_status='submitted',
            notes='Application submitted'
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a draft application."""
        application = self.get_object()

        if application.status != 'draft':
            return Response({'error': 'Can only submit draft applications'}, status=400)

        old_status = application.status
        application.status = 'submitted'
        application.submitted_at = timezone.now()
        application.save(update_fields=['status', 'submitted_at'])

        # Create status history
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=old_status,
            to_status='submitted'
        )

        return Response({
            'id': str(application.id),
            'status': application.status,
            'submitted_at': application.submitted_at,
            'message': 'Application submitted'
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update application status."""
        application = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        changed_by_id = request.data.get('changed_by_id')

        if not new_status:
            return Response({'error': 'status is required'}, status=400)

        valid_statuses = [s[0] for s in Application.Status.choices]
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Must be one of: {valid_statuses}'}, status=400)

        old_status = application.status
        application.status = new_status

        if changed_by_id:
            application.reviewed_by_id = changed_by_id
            application.reviewed_at = timezone.now()

        application.save()

        # Create status history
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=changed_by_id,
            notes=notes
        )

        return Response({
            'id': str(application.id),
            'status': application.status,
            'message': f'Status updated to {new_status}'
        })

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw an application."""
        application = self.get_object()

        if application.status in ['accepted', 'rejected', 'withdrawn']:
            return Response({'error': 'Cannot withdraw this application'}, status=400)

        old_status = application.status
        application.status = 'withdrawn'
        application.save(update_fields=['status'])

        ApplicationStatusHistory.objects.create(
            application=application,
            from_status=old_status,
            to_status='withdrawn',
            notes='Withdrawn by applicant'
        )

        return Response({
            'id': str(application.id),
            'status': application.status,
            'message': 'Application withdrawn'
        })

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get applications by user ID."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        apps = self.queryset.filter(user_id=user_id)
        serializer = ApplicationListSerializer(apps, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_opportunity(self, request):
        """Get applications by opportunity ID."""
        opp_id = request.query_params.get('opportunity_id')
        if not opp_id:
            return Response({'error': 'opportunity_id is required'}, status=400)

        apps = self.queryset.filter(opportunity_id=opp_id)
        serializer = ApplicationListSerializer(apps, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_organization(self, request):
        """Get applications by organization ID."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id is required'}, status=400)

        apps = self.queryset.filter(opportunity__organization_id=org_id)
        serializer = ApplicationListSerializer(apps, many=True)
        return Response(serializer.data)


class InterviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Interviews.

    Endpoints:
    - GET /interviews/ - List all interviews
    - POST /interviews/ - Schedule new interview
    - GET /interviews/{id}/ - Get interview details
    - PUT/PATCH /interviews/{id}/ - Update interview
    - DELETE /interviews/{id}/ - Delete interview
    - POST /interviews/{id}/confirm/ - Confirm interview
    - POST /interviews/{id}/complete/ - Mark as completed
    - POST /interviews/{id}/cancel/ - Cancel interview
    - GET /interviews/by-application/ - Get interviews for an application
    - GET /interviews/upcoming/ - Get upcoming interviews
    """
    queryset = Interview.objects.select_related('application', 'application__user', 'application__opportunity')
    serializer_class = InterviewSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return InterviewCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return InterviewUpdateSerializer
        return InterviewSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        app_id = self.request.query_params.get('application_id')
        if app_id:
            queryset = queryset.filter(application_id=app_id)

        interview_status = self.request.query_params.get('status')
        if interview_status:
            queryset = queryset.filter(status=interview_status)

        interview_type = self.request.query_params.get('type')
        if interview_type:
            queryset = queryset.filter(interview_type=interview_type)

        return queryset

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm an interview."""
        interview = self.get_object()
        interview.status = 'confirmed'
        interview.save(update_fields=['status'])

        return Response({
            'id': str(interview.id),
            'status': interview.status,
            'message': 'Interview confirmed'
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark interview as completed."""
        interview = self.get_object()
        feedback = request.data.get('feedback', {})

        interview.status = 'completed'
        interview.feedback = feedback
        interview.save(update_fields=['status', 'feedback'])

        return Response({
            'id': str(interview.id),
            'status': interview.status,
            'message': 'Interview completed'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an interview."""
        interview = self.get_object()
        reason = request.data.get('reason', 'Cancelled')

        interview.status = 'cancelled'
        interview.notes = f"{interview.notes or ''}\n\nCancellation reason: {reason}".strip()
        interview.save(update_fields=['status', 'notes'])

        return Response({
            'id': str(interview.id),
            'status': interview.status,
            'message': 'Interview cancelled'
        })

    @action(detail=False, methods=['get'])
    def by_application(self, request):
        """Get interviews for an application."""
        app_id = request.query_params.get('application_id')
        if not app_id:
            return Response({'error': 'application_id is required'}, status=400)

        interviews = self.queryset.filter(application_id=app_id)
        serializer = self.get_serializer(interviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming interviews."""
        user_id = request.query_params.get('user_id')
        queryset = self.queryset.filter(
            status__in=['scheduled', 'confirmed'],
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at')

        if user_id:
            queryset = queryset.filter(application__user_id=user_id)

        serializer = self.get_serializer(queryset[:20], many=True)
        return Response(serializer.data)


class ApplicationStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for application status history."""
    queryset = ApplicationStatusHistory.objects.select_related('application', 'changed_by')
    serializer_class = ApplicationStatusHistorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        app_id = self.request.query_params.get('application_id')
        if app_id:
            queryset = queryset.filter(application_id=app_id)

        return queryset


# ============================================================
# Standalone API Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def applications_stats(request):
    """Get application statistics."""
    total = Application.objects.count()

    by_status = {}
    for app_status in Application.Status.choices:
        count = Application.objects.filter(status=app_status[0]).count()
        by_status[app_status[1]] = count

    interviews_scheduled = Interview.objects.filter(
        status__in=['scheduled', 'confirmed']
    ).count()

    return Response({
        'total_applications': total,
        'by_status': by_status,
        'interviews_scheduled': interviews_scheduled
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def interview_stats(request):
    """Get interview statistics."""
    total = Interview.objects.count()

    by_status = {}
    for int_status in Interview.Status.choices:
        count = Interview.objects.filter(status=int_status[0]).count()
        by_status[int_status[1]] = count

    by_type = {}
    for int_type in Interview.InterviewType.choices:
        count = Interview.objects.filter(interview_type=int_type[0]).count()
        by_type[int_type[1]] = count

    return Response({
        'total_interviews': total,
        'by_status': by_status,
        'by_type': by_type
    })

