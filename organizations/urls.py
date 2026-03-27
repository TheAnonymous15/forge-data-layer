# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Organization URLs
===============================================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import partner_views

router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet, basename='organization')
router.register(r'members', views.OrganizationMemberViewSet, basename='member')
router.register(r'locations', views.OrganizationLocationViewSet, basename='location')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.organizations_stats, name='organizations-stats'),
    
    # Partner Authentication (separate from talent auth)
    path('partners/auth/register/', partner_views.partner_register, name='partner-register'),
    path('partners/auth/login/', partner_views.partner_login, name='partner-login'),
    path('partners/auth/logout/', partner_views.partner_logout, name='partner-logout'),
    path('partners/auth/verify-email/', partner_views.partner_verify_email, name='partner-verify-email'),
    path('partners/auth/resend-verification/', partner_views.partner_resend_verification, name='partner-resend-verification'),
    path('partners/auth/password/reset/', partner_views.partner_password_reset_request, name='partner-password-reset'),
    path('partners/auth/password/reset/confirm/', partner_views.partner_password_reset_confirm, name='partner-password-reset-confirm'),
    path('partners/auth/password/reset/verify-token/', partner_views.partner_password_reset_verify_token, name='partner-password-reset-verify-token'),
]

