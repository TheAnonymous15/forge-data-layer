# -*- coding: utf-8 -*-
"""Tokens app URLs."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def tokens_root(request):
    """Tokens API root."""
    return Response({'message': 'Tokens API v1'})


urlpatterns = [
    path('', tokens_root, name='tokens-root'),
]

