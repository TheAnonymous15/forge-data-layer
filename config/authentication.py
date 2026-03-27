# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Service-to-Service Authentication
=====================================================
Custom authentication for other services calling the Data Layer.
"""
from rest_framework import authentication, exceptions
from django.conf import settings


class ServiceKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate service-to-service calls using API keys.

    Other microservices must include these headers:
    - X-Service-ID: The service identifier (e.g., 'talent-portal')
    - X-API-Key: The shared API key
    """

    def authenticate(self, request):
        service_id = request.META.get('HTTP_X_SERVICE_ID')
        api_key = request.META.get('HTTP_X_API_KEY')

        # If no service headers, let other auth methods handle it
        if not service_id and not api_key:
            return None

        # Both headers required for service auth
        if not service_id or not api_key:
            raise exceptions.AuthenticationFailed(
                'Both X-Service-ID and X-API-Key headers are required'
            )

        # Validate service ID
        allowed_services = getattr(settings, 'ALLOWED_SERVICE_IDS', [])
        if service_id not in allowed_services:
            raise exceptions.AuthenticationFailed(
                f'Unknown service: {service_id}'
            )

        # Validate API key
        expected_key = getattr(settings, 'DATA_LAYER_API_KEY', '')
        if api_key != expected_key:
            raise exceptions.AuthenticationFailed('Invalid API key')

        # Return a service user object
        return (ServiceUser(service_id), None)


class ServiceUser:
    """
    Represents an authenticated service (not a human user).
    Used for service-to-service authentication.
    """

    def __init__(self, service_id):
        self.service_id = service_id
        self.is_authenticated = True
        self.is_service = True

    def __str__(self):
        return f'Service: {self.service_id}'

    @property
    def is_anonymous(self):
        return False

