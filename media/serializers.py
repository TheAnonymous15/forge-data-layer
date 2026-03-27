# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Media Serializers
================================================
"""
from rest_framework import serializers
from .models import Document, Image, MediaProcessingLog


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload"""
    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(choices=Document.DOCUMENT_TYPES, default='other')
    owner_id = serializers.UUIDField()


class DocumentSerializer(serializers.ModelSerializer):
    """Full document serializer"""

    class Meta:
        model = Document
        fields = [
            'id', 'owner_id', 'title', 'description', 'document_type',
            'original_filename', 'original_size', 'mime_type',
            'extracted_text', 'parsed_data',
            'status', 'processing_error',
            'is_primary', 'is_verified', 'is_public',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight document list serializer"""

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'original_filename',
            'original_size', 'status', 'is_primary', 'created_at'
        ]


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for image upload"""
    file = serializers.ImageField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    image_type = serializers.ChoiceField(choices=Image.IMAGE_TYPES, default='other')
    owner_id = serializers.UUIDField()
    owner_type = serializers.CharField(max_length=20, default='user')


class ImageSerializer(serializers.ModelSerializer):
    """Full image serializer"""

    class Meta:
        model = Image
        fields = [
            'id', 'owner_id', 'owner_type', 'title', 'image_type',
            'original_filename', 'original_size', 'original_width', 'original_height',
            'mime_type',
            'thumbnail_url', 'medium_url', 'large_url', 'full_url',
            'thumbnail_size', 'medium_size', 'large_size', 'full_size',
            'status', 'processing_error',
            'is_primary', 'is_public',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at']


class ImageListSerializer(serializers.ModelSerializer):
    """Lightweight image list serializer"""

    class Meta:
        model = Image
        fields = [
            'id', 'title', 'image_type', 'thumbnail_url',
            'status', 'is_primary', 'created_at'
        ]


class MediaProcessingLogSerializer(serializers.ModelSerializer):
    """Processing log serializer"""

    class Meta:
        model = MediaProcessingLog
        fields = '__all__'

