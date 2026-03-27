# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer URLs
===================================
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Documentation UI (Root)
    path('', include('core.urls')),
    path('docs/', include('core.urls')),

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation (Swagger/OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API Service operations (handles API Service user management)
    path('api/v1/api-service/', include('api_service.urls')),

    # Data Layer operations (handles Data Layer user management)
    path('api/v1/data-layer/', include('data_layer.urls')),

    # Service Authentication (API Service & Data Layer user auth, access requests)
    path('api/v1/service-auth/', include('users.service_urls')),

    # Authentication (register, login, logout, password reset, etc.)
    path('api/v1/auth/', include('authentication.urls')),

    # Data Layer API v1
    path('api/v1/users/', include('users.urls')),
    path('api/v1/profiles/', include('profiles.urls')),
    path('api/v1/organizations/', include('organizations.urls')),
    path('api/v1/opportunities/', include('opportunities.urls')),
    path('api/v1/applications/', include('applications.urls')),
    path('api/v1/tokens/', include('tokens.urls')),
    path('api/v1/audit/', include('audit.urls')),
    path('api/v1/media/', include('media.urls')),

    # New subsystems
    path('api/v1/administration/', include('administration.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/communications/', include('communications.urls')),
    path('api/v1/intelligence/', include('intelligence.urls')),
    path('api/v1/matching/', include('matching.urls')),
    path('api/v1/security/', include('security.urls')),
    path('api/v1/storage/', include('storage.urls')),
    path('api/v1/website/', include('website.urls')),

    # Health check
    path('health/', include('users.health_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

