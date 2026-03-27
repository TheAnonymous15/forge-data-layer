# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Application URLs
==============================================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'applications'

router = DefaultRouter()
router.register(r'applications', views.ApplicationViewSet, basename='application')
router.register(r'interviews', views.InterviewViewSet, basename='interview')
router.register(r'status-history', views.ApplicationStatusHistoryViewSet, basename='status-history')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.applications_stats, name='applications-stats'),
    path('interviews/stats/', views.interview_stats, name='interview-stats'),
]

