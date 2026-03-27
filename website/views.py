# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Website Views
============================================
Blog management endpoints only.
"""
import logging
from django.db.models import Q, F
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import BlogPost, BlogImage
from .serializers import (
    BlogPostSerializer, BlogPostListSerializer, BlogImageSerializer
)

logger = logging.getLogger(__name__)


class BlogPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'per_page'
    max_page_size = 50


class BlogPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Blog Posts.

    Endpoints:
    - GET /blog/ - List all published posts
    - POST /blog/ - Create new post (admin)
    - GET /blog/{id}/ - Get post by ID
    - GET /blog/by-slug/{slug}/ - Get post by slug
    - PUT/PATCH /blog/{id}/ - Update post
    - DELETE /blog/{id}/ - Delete post
    - POST /blog/{id}/view/ - Increment view count
    - POST /blog/{id}/like/ - Like a post
    - GET /blog/featured/ - Get featured posts
    - GET /blog/categories/ - Get all categories
    """
    queryset = BlogPost.objects.prefetch_related('images')
    serializer_class = BlogPostSerializer
    permission_classes = [AllowAny]
    pagination_class = BlogPagination
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'list':
            return BlogPostListSerializer
        return BlogPostSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'by_slug', 'view', 'like', 'featured', 'categories']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # By default, only show published posts for public
        if self.action == 'list' and not getattr(self.request.user, 'is_staff', False):
            queryset = queryset.filter(status='published')

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)

        # Filter by tag
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        # Filter by featured
        featured = self.request.query_params.get('featured')
        if featured is not None:
            queryset = queryset.filter(is_featured=featured.lower() == 'true')

        # Filter by status (admin only)
        post_status = self.request.query_params.get('status')
        if post_status and getattr(self.request.user, 'is_staff', False):
            queryset = queryset.filter(status=post_status)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'], url_path='by-slug/(?P<slug>[^/.]+)')
    def by_slug(self, request, slug=None):
        """Get blog post by slug."""
        try:
            post = self.queryset.get(slug=slug)
            # Check if published for non-staff
            if post.status != 'published' and not getattr(request.user, 'is_staff', False):
                return Response({'error': 'Post not found'}, status=404)
            serializer = self.get_serializer(post)
            return Response(serializer.data)
        except BlogPost.DoesNotExist:
            return Response({'error': 'Post not found'}, status=404)

    @action(detail=True, methods=['post'])
    def view(self, request, id=None):
        """Increment view count for a post."""
        post = self.get_object()
        post.views_count = F('views_count') + 1
        post.save(update_fields=['views_count'])
        post.refresh_from_db()
        return Response({'success': True, 'views_count': post.views_count})

    @action(detail=True, methods=['post'])
    def like(self, request, id=None):
        """Like a post."""
        post = self.get_object()
        post.likes_count = F('likes_count') + 1
        post.save(update_fields=['likes_count'])
        post.refresh_from_db()
        return Response({'success': True, 'likes_count': post.likes_count})

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured posts."""
        posts = self.queryset.filter(is_featured=True, status='published')[:6]
        serializer = BlogPostListSerializer(posts, many=True)
        return Response({'success': True, 'posts': serializer.data})

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all unique categories."""
        categories = BlogPost.objects.filter(status='published').values_list(
            'category', flat=True
        ).distinct()
        return Response({'success': True, 'categories': list(filter(None, categories))})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent posts."""
        limit = int(request.query_params.get('limit', 5))
        posts = self.queryset.filter(status='published').order_by('-published_at')[:limit]
        serializer = BlogPostListSerializer(posts, many=True)
        return Response({'success': True, 'posts': serializer.data})


class BlogImageViewSet(viewsets.ModelViewSet):
    """ViewSet for Blog Images."""
    queryset = BlogImage.objects.all()
    serializer_class = BlogImageSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        post_id = self.request.query_params.get('post_id')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset


@api_view(['GET'])
@permission_classes([AllowAny])
def website_stats(request):
    """Get public website statistics."""
    try:
        from users.models import User
        from profiles.models import TalentProfile
        from organizations.models import Organization
        from opportunities.models import Opportunity

        return Response({
            'success': True,
            'data': {
                'talents_count': TalentProfile.objects.count(),
                'organizations_count': Organization.objects.count(),
                'opportunities_count': Opportunity.objects.filter(status='published').count(),
                'blog_posts_count': BlogPost.objects.filter(status='published').count(),
                'countries_count': 54,  # African countries
            }
        })
    except Exception as e:
        logger.error(f"Error getting website stats: {e}")
        return Response({
            'success': True,
            'data': {
                'talents_count': 0,
                'organizations_count': 0,
                'opportunities_count': 0,
                'blog_posts_count': BlogPost.objects.filter(status='published').count(),
                'countries_count': 54,
            }
        })

