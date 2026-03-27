# -*- coding: utf-8 -*-
"""Analytics API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'analytics'

router = DefaultRouter()
router.register(r'pageviews', views.PageViewViewSet, basename='pageview')
router.register(r'events', views.UserEventViewSet, basename='event')
router.register(r'metrics', views.PlatformMetricViewSet, basename='metric')
router.register(r'reports', views.ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]

