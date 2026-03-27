# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer URLs
===================================
URL routing for Data Layer operations only.
"""
from django.urls import path
from . import views

app_name = 'data_layer'

urlpatterns = [
    # Authentication
    path('auth/login/', views.data_layer_login, name='login'),
    path('auth/logout/', views.data_layer_logout, name='logout'),
    path('auth/change-password/', views.change_password, name='change_password'),

    # Access Requests
    path('access-requests/', views.create_access_request, name='create_access_request'),
    path('access-requests/list/', views.list_access_requests, name='list_access_requests'),
    path('access-requests/<uuid:request_id>/', views.get_access_request, name='get_access_request'),
    path('access-requests/<uuid:request_id>/approve/', views.approve_access_request, name='approve_access_request'),
    path('access-requests/<uuid:request_id>/reject/', views.reject_access_request, name='reject_access_request'),
    path('users/', views.list_users, name='list_users'),
    path('users/<uuid:user_id>/', views.get_user, name='get_user'),
    path('health/', views.health_check, name='health'),
]

