# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Website Serializers
==================================================
Blog posts and images only.
"""
from rest_framework import serializers
from .models import BlogPost, BlogImage


class BlogImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogImage
        fields = ['id', 'post', 'image_url', 'alt_text', 'caption', 'position', 'created_at']
        read_only_fields = ['id', 'created_at']


class BlogPostSerializer(serializers.ModelSerializer):
    images = BlogImageSerializer(many=True, read_only=True)
    author_display = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content',
            'author', 'author_name', 'author_display',
            'featured_image', 'category', 'tags',
            'status', 'published_at',
            'meta_title', 'meta_description',
            'views_count', 'likes_count',
            'is_featured', 'allow_comments',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'views_count', 'likes_count', 'created_at', 'updated_at']

    def get_author_display(self, obj):
        if obj.author_name:
            return obj.author_name
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email
        return "ForgeForth Africa"


class BlogPostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing blog posts."""
    author_display = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image',
            'category', 'tags', 'author_display',
            'published_at', 'views_count', 'is_featured'
        ]

    def get_author_display(self, obj):
        if obj.author_name:
            return obj.author_name
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email
        return "ForgeForth Africa"


class BlogPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating blog posts."""
    class Meta:
        model = BlogPost
        fields = [
            'title', 'excerpt', 'content', 'author', 'author_name',
            'featured_image', 'category', 'tags', 'status', 'published_at',
            'meta_title', 'meta_description', 'is_featured', 'allow_comments'
        ]

