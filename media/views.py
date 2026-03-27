# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Media Views
==========================================
Endpoints for document and image processing
"""
import os
import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings

from .models import Document, Image, MediaProcessingLog
from .serializers import (
    DocumentSerializer, DocumentListSerializer, DocumentUploadSerializer,
    ImageSerializer, ImageListSerializer, ImageUploadSerializer,
    MediaProcessingLogSerializer
)
from .services import DocumentProcessor, ImageProcessor

logger = logging.getLogger('data_layer.media')


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for document operations"""
    queryset = Document.objects.all()
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer

    def get_queryset(self):
        queryset = Document.objects.all()
        owner_id = self.request.query_params.get('owner_id')
        document_type = self.request.query_params.get('document_type')

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        return queryset

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload and process a document.
        Pipeline: Validate → Sanitize → Extract Text → Store
        """
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Read file content
        file_content = file.read()

        # Process document
        processor = DocumentProcessor()
        start_time = datetime.now()
        result = processor.process(
            file_content,
            file.name,
            serializer.validated_data.get('document_type', 'other')
        )
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if not result['success']:
            return Response({
                'error': 'Document processing failed',
                'details': result.get('steps', [])
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create document record
        document = Document.objects.create(
            owner_id=serializer.validated_data['owner_id'],
            title=serializer.validated_data.get('title', file.name),
            description=serializer.validated_data.get('description', ''),
            document_type=serializer.validated_data.get('document_type', 'other'),
            original_filename=file.name,
            original_size=len(file_content),
            mime_type=file.content_type,
            extracted_text=result.get('extracted_text', ''),
            status='processed',
            processed_at=datetime.now()
        )

        # Save processed file
        if result.get('content'):
            from django.core.files.base import ContentFile
            document.original_file.save(
                f"{document.id}.bin",
                ContentFile(result['content']),
                save=True
            )

        # Log processing
        MediaProcessingLog.objects.create(
            media_type='document',
            media_id=document.id,
            operation='upload_process',
            status='success',
            input_size=len(file_content),
            output_size=result.get('final_size', len(file_content)),
            processing_time_ms=int(processing_time),
            metadata={'steps': result.get('steps', [])}
        )

        return Response({
            'success': True,
            'document': DocumentSerializer(document).data,
            'processing': result.get('steps', [])
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def parse(self, request, pk=None):
        """
        Trigger AI parsing for a document (CV extraction).
        This would integrate with AI services for full parsing.
        """
        document = self.get_object()

        # Placeholder for AI parsing
        # In production, this would call an AI service
        parsed_data = {
            'parsed_at': datetime.now().isoformat(),
            'method': 'placeholder',
            'note': 'Full AI parsing not implemented'
        }

        document.parsed_data = parsed_data
        document.save()

        return Response({
            'success': True,
            'parsed_data': parsed_data
        })

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set this document as the primary document for its type"""
        document = self.get_object()

        # Unset other primary documents of same type for owner
        Document.objects.filter(
            owner_id=document.owner_id,
            document_type=document.document_type,
            is_primary=True
        ).update(is_primary=False)

        document.is_primary = True
        document.save()

        return Response({
            'success': True,
            'document': DocumentSerializer(document).data
        })


class ImageViewSet(viewsets.ModelViewSet):
    """ViewSet for image operations"""
    queryset = Image.objects.all()
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return ImageListSerializer
        return ImageSerializer

    def get_queryset(self):
        queryset = Image.objects.all()
        owner_id = self.request.query_params.get('owner_id')
        owner_type = self.request.query_params.get('owner_type')
        image_type = self.request.query_params.get('image_type')

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        if owner_type:
            queryset = queryset.filter(owner_type=owner_type)
        if image_type:
            queryset = queryset.filter(image_type=image_type)

        return queryset

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload and process an image.
        Pipeline: Validate → Sanitize → Compress to WebP → Create Versions → Store
        """
        serializer = ImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Read file content
        file_content = file.read()

        # Get image dimensions
        from PIL import Image as PILImage
        import io
        try:
            img = PILImage.open(io.BytesIO(file_content))
            original_width, original_height = img.size
        except Exception as e:
            return Response({
                'error': f'Invalid image file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Process image
        processor = ImageProcessor()
        start_time = datetime.now()
        result = processor.process(file_content, file.name, create_versions=True)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if not result['success']:
            return Response({
                'error': 'Image processing failed',
                'details': result.get('steps', [])
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create image record
        image = Image.objects.create(
            owner_id=serializer.validated_data['owner_id'],
            owner_type=serializer.validated_data.get('owner_type', 'user'),
            title=serializer.validated_data.get('title', ''),
            image_type=serializer.validated_data.get('image_type', 'other'),
            original_filename=file.name,
            original_size=len(file_content),
            original_width=original_width,
            original_height=original_height,
            mime_type=file.content_type,
            status='processed',
            processed_at=datetime.now()
        )

        # Store versions metadata
        versions = result.get('versions', {})
        if 'thumbnail' in versions:
            image.thumbnail_size = versions['thumbnail'].get('size', 0)
        if 'medium' in versions:
            image.medium_size = versions['medium'].get('size', 0)
        if 'large' in versions:
            image.large_size = versions['large'].get('size', 0)
        if 'full' in versions:
            image.full_size = versions['full'].get('final_size', 0)

        image.save()

        # Save original file
        if result.get('content'):
            from django.core.files.base import ContentFile
            image.original_file.save(
                f"{image.id}.webp",
                ContentFile(result['content']),
                save=True
            )

        # Log processing
        MediaProcessingLog.objects.create(
            media_type='image',
            media_id=image.id,
            operation='upload_process',
            status='success',
            input_size=len(file_content),
            output_size=image.full_size or len(file_content),
            processing_time_ms=int(processing_time),
            metadata={
                'steps': result.get('steps', []),
                'versions': list(versions.keys())
            }
        )

        return Response({
            'success': True,
            'image': ImageSerializer(image).data,
            'processing': result.get('steps', []),
            'versions': versions
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set this image as the primary image for its type"""
        image = self.get_object()

        # Unset other primary images of same type for owner
        Image.objects.filter(
            owner_id=image.owner_id,
            owner_type=image.owner_type,
            image_type=image.image_type,
            is_primary=True
        ).update(is_primary=False)

        image.is_primary = True
        image.save()

        return Response({
            'success': True,
            'image': ImageSerializer(image).data
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def media_health(request):
    """Health check for media service"""
    return Response({
        'status': 'healthy',
        'service': 'data_layer_media',
        'timestamp': datetime.now().isoformat()
    })


# =============================================================================
# Document Additional Endpoints
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def document_stats(request):
    """Get document statistics for a user."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    from django.db.models import Sum, Count
    
    queryset = Document.objects.filter(owner_id=user_id)
    stats = queryset.aggregate(
        total=Count('id'),
        total_size=Sum('original_size'),
    )
    
    # Count by document type
    by_type = queryset.values('document_type').annotate(
        count=Count('id')
    )
    type_counts = {item['document_type']: item['count'] for item in by_type}
    
    return Response({
        'success': True,
        'stats': {
            'total': stats['total'] or 0,
            'total_size': stats['total_size'] or 0,
            'resumes': type_counts.get('resume', 0),
            'cover_letters': type_counts.get('cover_letter', 0),
            'certificates': type_counts.get('certificate', 0),
            'portfolios': type_counts.get('portfolio', 0),
            'other': type_counts.get('other', 0),
        }
    })


@api_view(['PATCH', 'POST'])
@permission_classes([AllowAny])
def document_rename(request, pk):
    """Rename a document."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
    
    new_title = request.data.get('title')
    if not new_title:
        return Response({'error': 'title is required'}, status=400)
    
    document.title = new_title
    document.save(update_fields=['title'])
    
    return Response({
        'success': True,
        'document': DocumentSerializer(document).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def document_preview(request, pk):
    """Get document preview URL or generate preview content."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
    
    # For text-based documents, return extracted text preview
    preview_content = None
    if document.extracted_text:
        # Return first 1000 chars as preview
        preview_content = document.extracted_text[:1000]
        if len(document.extracted_text) > 1000:
            preview_content += '...'
    
    preview_url = None
    if document.original_file:
        preview_url = document.original_file.url
    
    return Response({
        'success': True,
        'document_id': str(document.id),
        'title': document.title,
        'mime_type': document.mime_type,
        'preview_url': preview_url,
        'preview_content': preview_content,
        'can_preview': document.mime_type in ['application/pdf', 'text/plain', 'text/html'],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def document_download(request, pk):
    """Get document download URL."""
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
    
    if not document.original_file:
        return Response({'error': 'Document file not available'}, status=404)
    
    # Increment download count if tracked
    if hasattr(document, 'download_count'):
        document.download_count = (document.download_count or 0) + 1
        document.save(update_fields=['download_count'])
    
    return Response({
        'success': True,
        'document_id': str(document.id),
        'filename': document.original_filename or document.title,
        'mime_type': document.mime_type,
        'file_size': document.original_size,
        'download_url': document.original_file.url,
    })


# =============================================================================
# Resume Builder
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def resume_get(request):
    """Get user's resume data from their profile."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    # Get resume document if exists
    resume_doc = Document.objects.filter(
        owner_id=user_id, 
        document_type='resume',
        is_primary=True
    ).first()
    
    # This would integrate with the profile service for full data
    # For now, return the resume document info
    return Response({
        'success': True,
        'user_id': user_id,
        'has_resume': resume_doc is not None,
        'resume_document': DocumentSerializer(resume_doc).data if resume_doc else None,
        'template': 'modern',  # Default template
        'last_updated': resume_doc.updated_at.isoformat() if resume_doc else None,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resume_save(request):
    """Save resume data."""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    resume_data = request.data.get('resume_data', {})
    template = request.data.get('template', 'modern')
    
    # Get or create resume document record
    resume_doc, created = Document.objects.get_or_create(
        owner_id=user_id,
        document_type='resume',
        is_primary=True,
        defaults={
            'title': 'My Resume',
            'description': 'Auto-generated resume',
            'mime_type': 'application/json',
            'parsed_data': {'template': template, 'data': resume_data}
        }
    )
    
    if not created:
        resume_doc.parsed_data = {'template': template, 'data': resume_data}
        resume_doc.save(update_fields=['parsed_data', 'updated_at'])
    
    return Response({
        'success': True,
        'message': 'Resume saved successfully',
        'document_id': str(resume_doc.id),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resume_analyze(request):
    """Analyze resume for ATS compatibility."""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    # Get resume content
    resume_doc = Document.objects.filter(
        owner_id=user_id, 
        document_type='resume'
    ).first()
    
    # Placeholder ATS analysis - would integrate with AI service
    analysis = {
        'ats_score': 75,
        'sections': {
            'contact_info': {'score': 100, 'status': 'complete'},
            'summary': {'score': 80, 'status': 'good', 'suggestion': 'Add more keywords'},
            'experience': {'score': 70, 'status': 'needs_improvement', 'suggestion': 'Use action verbs'},
            'education': {'score': 90, 'status': 'good'},
            'skills': {'score': 60, 'status': 'needs_improvement', 'suggestion': 'Add more relevant skills'},
        },
        'keywords_found': ['Python', 'Django', 'JavaScript'],
        'missing_keywords': ['Leadership', 'Communication', 'Problem-solving'],
        'formatting': {
            'score': 85,
            'issues': ['Consider using bullet points consistently']
        }
    }
    
    return Response({
        'success': True,
        'analysis': analysis,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def resume_suggestions(request):
    """Get AI-powered suggestions for resume improvement."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    # Placeholder suggestions - would integrate with AI service
    suggestions = [
        {
            'section': 'summary',
            'type': 'improvement',
            'priority': 'high',
            'suggestion': 'Add a compelling professional summary that highlights your key achievements',
            'example': 'Results-driven software engineer with 5+ years of experience...'
        },
        {
            'section': 'experience',
            'type': 'improvement',
            'priority': 'medium',
            'suggestion': 'Quantify your achievements with metrics',
            'example': 'Increased team productivity by 25% through process automation'
        },
        {
            'section': 'skills',
            'type': 'addition',
            'priority': 'medium',
            'suggestion': 'Add in-demand skills relevant to your target roles',
            'recommended': ['Cloud Computing', 'Agile Methodologies', 'Data Analysis']
        },
    ]
    
    return Response({
        'success': True,
        'suggestions': suggestions,
        'total_suggestions': len(suggestions),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resume_export_pdf(request):
    """Export resume as PDF."""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    template = request.data.get('template', 'modern')
    
    # This would integrate with a PDF generation service
    # For now, return a placeholder response
    return Response({
        'success': True,
        'message': 'PDF generation initiated',
        'status': 'processing',
        'job_id': 'pdf-export-placeholder',
        'note': 'PDF generation service integration pending'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resume_export_html(request):
    """Export resume as HTML."""
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    template = request.data.get('template', 'modern')
    
    # Get resume data
    resume_doc = Document.objects.filter(
        owner_id=user_id, 
        document_type='resume'
    ).first()
    
    # Generate basic HTML - would use templates in production
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Resume</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .section { margin-bottom: 20px; }
            .section-title { color: #666; border-bottom: 1px solid #ccc; }
        </style>
    </head>
    <body>
        <h1>Resume</h1>
        <p>Resume content would be rendered here from profile data.</p>
    </body>
    </html>
    """
    
    return Response({
        'success': True,
        'html_content': html_content,
        'content_type': 'text/html',
    })

