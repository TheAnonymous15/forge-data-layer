# -*- coding: utf-8 -*-
"""Storage API Views."""
import secrets
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from .models import StorageBucket, StoredFile, FileAccess, ShareLink
from .serializers import StorageBucketSerializer, StoredFileSerializer, FileAccessSerializer, ShareLinkSerializer


class StorageBucketViewSet(viewsets.ModelViewSet):
    """API endpoint for storage buckets."""
    queryset = StorageBucket.objects.all()
    serializer_class = StorageBucketSerializer
    permission_classes = [IsAuthenticated]


class StoredFileViewSet(viewsets.ModelViewSet):
    """API endpoint for stored files."""
    serializer_class = StoredFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return StoredFile.objects.filter(owner=self.request.user).select_related('bucket')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a file."""
        file = self.get_object()

        # Log access
        FileAccess.objects.create(
            file=file,
            user=request.user,
            access_type='download',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # Update access count
        from django.utils import timezone
        file.access_count += 1
        file.last_accessed_at = timezone.now()
        file.save(update_fields=['access_count', 'last_accessed_at'])

        # In production, this would return the actual file or a presigned URL
        return Response({
            'success': True,
            'file_path': file.file_path,
            'original_name': file.original_name,
            'content_type': file.content_type
        })

    @action(detail=True, methods=['post'])
    def create_share_link(self, request, pk=None):
        """Create a share link for a file."""
        file = self.get_object()

        expires_in_hours = request.data.get('expires_in_hours')
        max_downloads = request.data.get('max_downloads')
        password = request.data.get('password')

        from django.utils import timezone
        from datetime import timedelta
        import hashlib

        link = ShareLink.objects.create(
            file=file,
            created_by=request.user,
            token=secrets.token_urlsafe(32),
            is_password_protected=bool(password),
            password_hash=hashlib.sha256(password.encode()).hexdigest() if password else '',
            max_downloads=max_downloads,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
        )

        return Response({
            'success': True,
            'data': ShareLinkSerializer(link, context={'request': request}).data
        })


class ShareLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for share links."""
    queryset = ShareLink.objects.filter(is_active=True)
    serializer_class = ShareLinkSerializer
    permission_classes = [AllowAny]
    lookup_field = 'token'

    @action(detail=True, methods=['post'], url_path='access')
    def access(self, request, token=None):
        """Access a shared file."""
        try:
            link = ShareLink.objects.get(token=token, is_active=True)
        except ShareLink.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid or expired link'}, status=404)

        from django.utils import timezone

        # Check expiration
        if link.expires_at and link.expires_at < timezone.now():
            return Response({'success': False, 'error': 'Link has expired'}, status=410)

        # Check max downloads
        if link.max_downloads and link.download_count >= link.max_downloads:
            return Response({'success': False, 'error': 'Maximum downloads reached'}, status=410)

        # Check password if required
        if link.is_password_protected:
            import hashlib
            password = request.data.get('password', '')
            if hashlib.sha256(password.encode()).hexdigest() != link.password_hash:
                return Response({'success': False, 'error': 'Invalid password'}, status=403)

        # Increment download count
        link.download_count += 1
        link.save(update_fields=['download_count'])

        # Log access
        FileAccess.objects.create(
            file=link.file,
            user=request.user if request.user.is_authenticated else None,
            access_type='share_download',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        file = link.file
        return Response({
            'success': True,
            'file': StoredFileSerializer(file).data
        })

