# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Organization Views
=================================================
Complete CRUD endpoints for organizations.
"""
import logging
from django.utils.text import slugify
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q, Count

from .models import Organization, OrganizationMember, OrganizationLocation
from .serializers import (
    OrganizationSerializer, OrganizationListSerializer,
    OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMemberSerializer, OrganizationLocationSerializer
)

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organizations.

    Endpoints:
    - GET /organizations/ - List all organizations
    - POST /organizations/ - Create new organization
    - GET /organizations/{id}/ - Get organization details
    - PUT/PATCH /organizations/{id}/ - Update organization
    - DELETE /organizations/{id}/ - Delete organization
    - GET /organizations/{id}/full/ - Get full organization with members/locations
    - POST /organizations/{id}/verify/ - Verify organization
    - GET /organizations/by-owner/ - Get organizations by owner
    """
    queryset = Organization.objects.select_related('owner').prefetch_related('members', 'locations')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        elif self.action == 'create':
            return OrganizationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrganizationUpdateSerializer
        return OrganizationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by owner
        owner_id = self.request.query_params.get('owner_id')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        # Filter by type
        org_type = self.request.query_params.get('type')
        if org_type:
            queryset = queryset.filter(org_type=org_type)

        # Filter by industry
        industry = self.request.query_params.get('industry')
        if industry:
            queryset = queryset.filter(industry__icontains=industry)

        # Filter by verification status
        verification = self.request.query_params.get('verification_status')
        if verification:
            queryset = queryset.filter(verification_status=verification)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by featured
        is_featured = self.request.query_params.get('is_featured')
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(industry__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        # Generate slug from name
        name = serializer.validated_data.get('name')
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        serializer.save(slug=slug)

    @action(detail=True, methods=['get'])
    def full(self, request, pk=None):
        """Get full organization details."""
        org = self.get_object()
        serializer = OrganizationSerializer(org)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify or reject an organization."""
        org = self.get_object()
        new_status = request.data.get('status', 'verified')
        if new_status not in ['verified', 'rejected', 'pending']:
            return Response({'error': 'Invalid status'}, status=400)

        org.verification_status = new_status
        org.save(update_fields=['verification_status'])

        return Response({
            'id': str(org.id),
            'verification_status': org.verification_status,
            'message': f'Organization {new_status}'
        })

    @action(detail=False, methods=['get'])
    def by_owner(self, request):
        """Get organizations by owner ID."""
        owner_id = request.query_params.get('owner_id')
        if not owner_id:
            return Response({'error': 'owner_id is required'}, status=400)

        orgs = self.queryset.filter(owner_id=owner_id)
        serializer = OrganizationListSerializer(orgs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured organizations."""
        orgs = self.queryset.filter(is_featured=True, is_active=True)[:10]
        serializer = OrganizationListSerializer(orgs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def industries(self, request):
        """Get list of unique industries."""
        industries = Organization.objects.values_list('industry', flat=True).distinct()
        return Response([i for i in industries if i])


class OrganizationMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization Members.

    Endpoints:
    - GET /members/ - List all members
    - POST /members/ - Add member to organization
    - GET /members/{id}/ - Get member details
    - PUT/PATCH /members/{id}/ - Update member
    - DELETE /members/{id}/ - Remove member
    - GET /members/by-organization/ - Get members for an organization
    - GET /members/by-user/ - Get memberships for a user
    """
    queryset = OrganizationMember.objects.select_related('organization', 'user', 'invited_by')
    serializer_class = OrganizationMemberSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        return queryset

    @action(detail=False, methods=['get'])
    def by_organization(self, request):
        """Get all members for an organization."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id is required'}, status=400)

        members = self.queryset.filter(organization_id=org_id)
        serializer = self.get_serializer(members, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get all organization memberships for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        memberships = self.queryset.filter(user_id=user_id)
        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)


class OrganizationLocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization Locations.

    Endpoints:
    - GET /locations/ - List all locations
    - POST /locations/ - Add location
    - GET /locations/{id}/ - Get location details
    - PUT/PATCH /locations/{id}/ - Update location
    - DELETE /locations/{id}/ - Delete location
    - GET /locations/by-organization/ - Get locations for an organization
    """
    queryset = OrganizationLocation.objects.select_related('organization')
    serializer_class = OrganizationLocationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_organization(self, request):
        """Get all locations for an organization."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id is required'}, status=400)

        locations = self.queryset.filter(organization_id=org_id)
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def organizations_stats(request):
    """Get organization statistics."""
    total = Organization.objects.count()
    verified = Organization.objects.filter(verification_status='verified').count()
    active = Organization.objects.filter(is_active=True).count()

    by_type = {}
    for org_type in Organization.Type.choices:
        count = Organization.objects.filter(org_type=org_type[0]).count()
        by_type[org_type[1]] = count

    by_size = {}
    for size in Organization.Size.choices:
        count = Organization.objects.filter(size=size[0]).count()
        by_size[size[1]] = count

    return Response({
        'total_organizations': total,
        'verified': verified,
        'active': active,
        'by_type': by_type,
        'by_size': by_size
    })

