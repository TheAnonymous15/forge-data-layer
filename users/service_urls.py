# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Service Authentication URLs
==========================================================
Internal authentication endpoints for API Service and Data Layer users.
These are NOT for end users - they're for service-level authentication.
"""
from django.urls import path
from . import service_views

urlpatterns = [
    # ==========================================================================
    # API Service Authentication
    # ==========================================================================
    path('api-service/login/', service_views.api_service_login, name='api-service-login'),
    path('api-service/verify/', service_views.api_service_verify, name='api-service-verify'),
    path('api-service/users/', service_views.list_api_service_users, name='api-service-users'),
    path('api-service/users/<uuid:user_id>/', service_views.manage_api_service_user, name='api-service-user-manage'),

    # ==========================================================================
    # Data Layer Authentication
    # ==========================================================================
    path('data-layer/login/', service_views.data_layer_login, name='data-layer-login'),
    path('data-layer/verify/', service_views.data_layer_verify, name='data-layer-verify'),
    path('data-layer/users/', service_views.list_data_layer_users, name='data-layer-users'),
    path('data-layer/users/<uuid:user_id>/', service_views.manage_data_layer_user, name='data-layer-user-manage'),

    # ==========================================================================
    # Access Requests
    # ==========================================================================
    path('access-request/', service_views.create_access_request, name='access-request'),  # POST - singular form
    path('access-requests/', service_views.list_access_requests, name='access-requests'),
    path('access-requests/create/', service_views.create_access_request, name='access-request-create'),
    path('access-requests/<uuid:request_id>/approve/', service_views.approve_access_request, name='access-request-approve'),
    path('access-requests/<uuid:request_id>/reject/', service_views.reject_access_request, name='access-request-reject'),
]

