# -*- coding: utf-8 -*-
"""Security API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'security'

router = DefaultRouter()
router.register(r'api-keys', views.APIKeyViewSet, basename='api-key')
router.register(r'events', views.SecurityEventViewSet, basename='event')
router.register(r'consent', views.ConsentRecordViewSet, basename='consent')
router.register(r'blocked-ips', views.BlockedIPViewSet, basename='blocked-ip')

urlpatterns = [
    path('', include(router.urls)),
]

