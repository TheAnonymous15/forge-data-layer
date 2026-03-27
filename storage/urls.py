# -*- coding: utf-8 -*-
"""Storage API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'storage'

router = DefaultRouter()
router.register(r'buckets', views.StorageBucketViewSet, basename='bucket')
router.register(r'files', views.StoredFileViewSet, basename='file')
router.register(r'share', views.ShareLinkViewSet, basename='share')

urlpatterns = [
    path('', include(router.urls)),
]

