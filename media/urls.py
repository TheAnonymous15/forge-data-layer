# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Media URLs
=========================================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'media'

router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'images', views.ImageViewSet, basename='image')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.media_health, name='media-health'),
    
    # Document additional endpoints
    path('documents/stats/', views.document_stats, name='document-stats'),
    path('documents/<uuid:pk>/rename/', views.document_rename, name='document-rename'),
    path('documents/<uuid:pk>/preview/', views.document_preview, name='document-preview'),
    path('documents/<uuid:pk>/download/', views.document_download, name='document-download'),
    
    # Resume Builder
    path('resume/', views.resume_get, name='resume-get'),
    path('resume/save/', views.resume_save, name='resume-save'),
    path('resume/analyze/', views.resume_analyze, name='resume-analyze'),
    path('resume/suggestions/', views.resume_suggestions, name='resume-suggestions'),
    path('resume/export/pdf/', views.resume_export_pdf, name='resume-export-pdf'),
    path('resume/export/html/', views.resume_export_html, name='resume-export-html'),
]
