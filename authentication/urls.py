# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Authentication URLs
==================================================
"""
from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    # Registration & Login
    path('register/', views.register, name='register'),
    path('register/partner/', views.register_partner, name='register-partner'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # Password Management
    path('password/change/', views.change_password, name='password-change'),
    path('password/reset/', views.password_reset_request, name='password-reset'),
    path('password/reset/confirm/', views.password_reset_confirm, name='password-reset-confirm'),
    path('password/reset/verify-token/', views.password_reset_verify_token, name='password-reset-verify-token'),

    # Token Management
    path('token/refresh/', views.token_refresh, name='token-refresh'),
    path('token/verify/', views.token_verify, name='token-verify'),
    path('token/blacklist/', views.token_blacklist, name='token-blacklist'),

    # Email Verification
    path('verify-email/', views.verify_email, name='verify-email'),
    path('resend-verification/', views.resend_verification, name='resend-verification'),

    # Two-Factor Authentication
    path('2fa/enable/', views.enable_2fa, name='2fa-enable'),
    path('2fa/disable/', views.disable_2fa, name='2fa-disable'),
    path('2fa/verify/', views.verify_2fa, name='2fa-verify'),
    path('2fa/backup-codes/', views.get_backup_codes, name='2fa-backup-codes'),
    path('2fa/backup-codes/regenerate/', views.regenerate_backup_codes, name='2fa-regenerate-backup-codes'),

    # Session Management
    path('sessions/', views.get_sessions, name='sessions'),
    path('sessions/<uuid:session_id>/revoke/', views.revoke_session, name='revoke-session'),
    path('sessions/revoke-all/', views.revoke_all_sessions, name='revoke-all-sessions'),

    # Login History
    path('login-history/', views.login_history, name='login-history'),
]
