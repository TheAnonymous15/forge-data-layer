# -*- coding: utf-8 -*-
"""Audit app URLs."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def audit_root(request):
    """Audit API root."""
    return Response({'message': 'Audit API v1'})


urlpatterns = [
    path('', audit_root, name='audit-root'),
]

