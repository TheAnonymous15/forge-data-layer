# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Core URLs
========================================
"""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication (Page-based)
    path('login/', views.data_login, name='data-login'),
    path('logout/', views.data_logout, name='data-logout'),
    
    # AJAX Authentication (for session establishment)
    path('ajax/login/', views.ajax_login, name='ajax-login'),
    path('ajax/change-password/', views.ajax_change_password, name='ajax-change-password'),

    # Protected UI routes
    path('', views.docs_ui, name='docs'),
    path('docs/', views.docs_ui, name='docs-page'),
    path('health/', views.health_ui, name='health-ui'),

    # API endpoints (public health check)
    path('health/status/', views.health_check, name='health'),
    path('api/stats/', views.api_stats, name='api-stats'),
]



