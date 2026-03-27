# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Website URLs
==========================================
Blog management endpoints only.
Registration handled by talent/partner subsystems.
Messaging handled by communications subsystem.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BlogPostViewSet, BlogImageViewSet, website_stats

router = DefaultRouter()
router.register(r'blog', BlogPostViewSet, basename='blog')
router.register(r'blog-images', BlogImageViewSet, basename='blog-image')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', website_stats, name='website-stats'),
]

