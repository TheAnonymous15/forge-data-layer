# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Opportunity Views
================================================
Complete CRUD endpoints for opportunities.
"""
import logging
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q, F, Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Opportunity, SavedOpportunity
from .serializers import (
    OpportunitySerializer, OpportunityListSerializer,
    OpportunityCreateSerializer, SavedOpportunitySerializer
)

logger = logging.getLogger(__name__)


class OpportunityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Opportunities.

    Endpoints:
    - GET /opportunities/ - List all opportunities
    - POST /opportunities/ - Create new opportunity
    - GET /opportunities/{id}/ - Get opportunity details
    - PUT/PATCH /opportunities/{id}/ - Update opportunity
    - DELETE /opportunities/{id}/ - Delete opportunity
    - POST /opportunities/{id}/publish/ - Publish opportunity
    - POST /opportunities/{id}/close/ - Close opportunity
    - POST /opportunities/{id}/pause/ - Pause opportunity
    - GET /opportunities/by-organization/ - Get by organization
    - GET /opportunities/featured/ - Get featured opportunities
    - GET /opportunities/search/ - Search opportunities
    """
    queryset = Opportunity.objects.select_related('organization', 'posted_by')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return OpportunityListSerializer
        elif self.action == 'create':
            return OpportunityCreateSerializer
        return OpportunitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by organization
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        # Filter by status
        opp_status = self.request.query_params.get('status')
        if opp_status:
            queryset = queryset.filter(status=opp_status)

        # Filter by type
        opp_type = self.request.query_params.get('opportunity_type')
        if opp_type:
            queryset = queryset.filter(opportunity_type=opp_type)

        # Filter by experience level
        exp_level = self.request.query_params.get('experience_level')
        if exp_level:
            queryset = queryset.filter(experience_level=exp_level)

        # Filter by remote policy
        remote = self.request.query_params.get('remote_policy')
        if remote:
            queryset = queryset.filter(remote_policy=remote)

        # Filter by country
        country = self.request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)

        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)

        # Filter by featured
        is_featured = self.request.query_params.get('is_featured')
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(organization__name__icontains=search) |
                Q(category__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title')
        org = serializer.validated_data.get('organization')
        base_slug = slugify(f"{title}-{org.name}")
        slug = base_slug
        counter = 1
        while Opportunity.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        serializer.save(slug=slug)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        Opportunity.objects.filter(pk=instance.pk).update(views_count=F('views_count') + 1)
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an opportunity."""
        opportunity = self.get_object()

        if opportunity.status not in ['draft', 'paused']:
            return Response({'error': 'Can only publish draft or paused opportunities'}, status=400)

        opportunity.status = 'open'
        opportunity.published_at = timezone.now()
        opportunity.save(update_fields=['status', 'published_at'])

        return Response({
            'id': str(opportunity.id),
            'status': opportunity.status,
            'published_at': opportunity.published_at,
            'message': 'Opportunity published'
        })

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an opportunity."""
        opportunity = self.get_object()
        reason = request.data.get('reason', 'closed')

        opportunity.status = 'closed' if reason == 'closed' else 'filled'
        opportunity.save(update_fields=['status'])

        return Response({
            'id': str(opportunity.id),
            'status': opportunity.status,
            'message': 'Opportunity closed'
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an opportunity."""
        opportunity = self.get_object()

        if opportunity.status != 'open':
            return Response({'error': 'Can only pause open opportunities'}, status=400)

        opportunity.status = 'paused'
        opportunity.save(update_fields=['status'])

        return Response({
            'id': str(opportunity.id),
            'status': opportunity.status,
            'message': 'Opportunity paused'
        })

    @action(detail=False, methods=['get'])
    def by_organization(self, request):
        """Get opportunities by organization ID."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id is required'}, status=400)

        opportunities = self.queryset.filter(organization_id=org_id)
        serializer = OpportunityListSerializer(opportunities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured opportunities."""
        limit = int(request.query_params.get('limit', 10))
        opportunities = self.queryset.filter(
            is_featured=True,
            status='open'
        ).order_by('-published_at')[:limit]
        serializer = OpportunityListSerializer(opportunities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently published opportunities."""
        limit = int(request.query_params.get('limit', 20))
        opportunities = self.queryset.filter(
            status='open'
        ).order_by('-published_at')[:limit]
        serializer = OpportunityListSerializer(opportunities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all unique categories."""
        categories = Opportunity.objects.values_list('category', flat=True).distinct()
        return Response([c for c in categories if c])

    @action(detail=False, methods=['get'])
    def locations(self, request):
        """Get all unique locations."""
        countries = Opportunity.objects.values_list('country', flat=True).distinct()
        cities = Opportunity.objects.values_list('city', flat=True).distinct()
        return Response({
            'countries': [c for c in countries if c],
            'cities': [c for c in cities if c]
        })


class SavedOpportunityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Saved Opportunities.

    Endpoints:
    - GET /saved/ - List saved opportunities
    - POST /saved/ - Save an opportunity
    - DELETE /saved/{id}/ - Unsave opportunity
    - GET /saved/by-user/ - Get saved opportunities by user
    - GET /saved/check/ - Check if opportunity is saved
    """
    queryset = SavedOpportunity.objects.select_related('user', 'opportunity', 'opportunity__organization')
    serializer_class = SavedOpportunitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get saved opportunities for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        saved = self.queryset.filter(user_id=user_id)
        serializer = self.get_serializer(saved, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if an opportunity is saved by user."""
        user_id = request.query_params.get('user_id')
        opportunity_id = request.query_params.get('opportunity_id')

        if not user_id or not opportunity_id:
            return Response({'error': 'user_id and opportunity_id are required'}, status=400)

        is_saved = SavedOpportunity.objects.filter(
            user_id=user_id,
            opportunity_id=opportunity_id
        ).exists()

        return Response({'is_saved': is_saved})

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle save status for an opportunity."""
        user_id = request.data.get('user_id')
        opportunity_id = request.data.get('opportunity_id')

        if not user_id or not opportunity_id:
            return Response({'error': 'user_id and opportunity_id are required'}, status=400)

        existing = SavedOpportunity.objects.filter(
            user_id=user_id,
            opportunity_id=opportunity_id
        ).first()

        if existing:
            existing.delete()
            return Response({'is_saved': False, 'message': 'Opportunity unsaved'})
        else:
            SavedOpportunity.objects.create(
                user_id=user_id,
                opportunity_id=opportunity_id
            )
            return Response({'is_saved': True, 'message': 'Opportunity saved'})


# ============================================================
# Standalone API Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def opportunities_stats(request):
    """Get opportunity statistics."""
    total = Opportunity.objects.count()

    by_status = {}
    for opp_status in Opportunity.Status.choices:
        count = Opportunity.objects.filter(status=opp_status[0]).count()
        by_status[opp_status[1]] = count

    by_type = {}
    for opp_type in Opportunity.OpportunityType.choices:
        count = Opportunity.objects.filter(opportunity_type=opp_type[0]).count()
        by_type[opp_type[1]] = count

    by_remote = {}
    for remote in Opportunity.RemotePolicy.choices:
        count = Opportunity.objects.filter(remote_policy=remote[0]).count()
        by_remote[remote[1]] = count

    open_opportunities = Opportunity.objects.filter(status='open').count()
    featured_count = Opportunity.objects.filter(is_featured=True, status='open').count()
    total_views = Opportunity.objects.aggregate(total=Sum('views_count'))['total'] or 0
    total_applications = Opportunity.objects.aggregate(total=Sum('applications_count'))['total'] or 0

    return Response({
        'total_opportunities': total,
        'open_opportunities': open_opportunities,
        'featured_opportunities': featured_count,
        'total_views': total_views,
        'total_applications': total_applications,
        'by_status': by_status,
        'by_type': by_type,
        'by_remote_policy': by_remote
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def opportunity_by_slug(request, slug):
    """Get opportunity by slug."""
    try:
        opportunity = Opportunity.objects.select_related('organization', 'posted_by').get(slug=slug)
        # Increment view count
        Opportunity.objects.filter(pk=opportunity.pk).update(views_count=F('views_count') + 1)
        opportunity.refresh_from_db()
        serializer = OpportunitySerializer(opportunity)
        return Response(serializer.data)
    except Opportunity.DoesNotExist:
        return Response({'error': 'Opportunity not found'}, status=404)

