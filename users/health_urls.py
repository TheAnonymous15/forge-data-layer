# -*- coding: utf-8 -*-
"""
Health check URLs
"""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'service': 'data-layer',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })


urlpatterns = [
    path('', health_check, name='health_check'),
]

