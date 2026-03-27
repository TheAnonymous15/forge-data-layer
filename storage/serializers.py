# -*- coding: utf-8 -*-
"""Storage Serializers."""
from rest_framework import serializers
from .models import StorageBucket, StoredFile, FileAccess, ShareLink


class StorageBucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageBucket
        fields = '__all__'


class StoredFileSerializer(serializers.ModelSerializer):
    bucket_name = serializers.CharField(source='bucket.name', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = StoredFile
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'checksum', 'access_count', 'created_at', 'updated_at']

    def get_download_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/v1/storage/files/{obj.id}/download/')
        return None


class FileAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAccess
        fields = '__all__'


class ShareLinkSerializer(serializers.ModelSerializer):
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = ShareLink
        fields = ['id', 'file', 'token', 'is_password_protected', 'max_downloads', 'download_count', 'expires_at', 'is_active', 'created_at', 'share_url']
        read_only_fields = ['id', 'token', 'download_count', 'created_at']

    def get_share_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/v1/storage/share/{obj.token}/')
        return None

