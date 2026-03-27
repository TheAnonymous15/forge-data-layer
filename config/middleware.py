# -*- coding: utf-8 -*-
"""
Data Layer - Request Signing Middleware
=======================================
Verifies that incoming requests from the API service are properly signed.
Signs all responses back to the API service.

SECURITY FLOW:
==============
API Service -> Data Layer:
1. API Service signs request with: X-Request-Timestamp, X-Request-Signature, X-API-Key
2. Data Layer verifies signature matches using shared signing key
3. If valid, request proceeds; if invalid, request is REJECTED

Data Layer -> API Service:
1. Data Layer signs response with: X-Response-Timestamp, X-Response-Signature  
2. API Service verifies response signature
3. If valid, response is trusted; if invalid, response is suspect
"""
import hmac
import hashlib
import time
import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('data_layer.security')


class DataLayerSignatureMiddleware:
    """
    Middleware to verify request signatures from the API service.

    All requests must include:
    - X-Service-ID: Identifier of the calling service
    - X-API-Key: API key for authentication
    - X-Request-Timestamp: Unix timestamp of the request
    - X-Request-Signature: HMAC signature of the request
    
    All responses include:
    - X-Response-Timestamp: Unix timestamp of the response
    - X-Response-Signature: HMAC signature of the response
    """

    EXEMPT_PATHS = [
        '/admin/',
        '/health/',
        '/api/docs/',
        '/api/schema/',
        '/api/redoc/',
        '/static/',
        '/media/',
        '/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.signing_key = getattr(settings, 'DATA_LAYER_SIGNING_KEY', settings.SECRET_KEY)
        self.api_key = getattr(settings, 'DATA_LAYER_API_KEY', 'data-layer-api-key')
        self.max_timestamp_diff = 300
        self.require_signing = getattr(settings, 'REQUIRE_DATA_LAYER_SIGNING', not settings.DEBUG)

    def __call__(self, request):
        if self._is_exempt(request.path):
            response = self.get_response(request)
            return self._sign_response(response)

        if not self.require_signing:
            signature = request.headers.get('X-Request-Signature', '')
            if not signature:
                logger.debug(f"Unsigned request to {request.path} (dev mode)")
                response = self.get_response(request)
                return self._sign_response(response)

        api_key = request.headers.get('X-API-Key', '')
        if api_key != self.api_key:
            logger.warning(f"Invalid API key from {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': {'code': 'INVALID_API_KEY', 'message': 'Invalid or missing API key'}
            }, status=401)

        timestamp_str = request.headers.get('X-Request-Timestamp', '')
        try:
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            if abs(current_time - timestamp) > self.max_timestamp_diff:
                logger.warning(f"Request timestamp too old/new: {timestamp}")
                return JsonResponse({
                    'success': False,
                    'error': {'code': 'INVALID_TIMESTAMP', 'message': 'Request timestamp is invalid or expired'}
                }, status=401)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': {'code': 'MISSING_TIMESTAMP', 'message': 'Request timestamp is required'}
            }, status=401)

        signature = request.headers.get('X-Request-Signature', '')
        if not signature:
            return JsonResponse({
                'success': False,
                'error': {'code': 'MISSING_SIGNATURE', 'message': 'Request signature is required'}
            }, status=401)

        method = request.method
        path = request.path
        body = request.body.decode('utf-8') if request.body else ''

        message = f"{method}|{path}|{body}|{timestamp_str}"
        expected_signature = hmac.new(
            self.signing_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning(f"Invalid signature for request to {path}")
            return JsonResponse({
                'success': False,
                'error': {'code': 'INVALID_SIGNATURE', 'message': 'Request signature verification failed'}
            }, status=401)

        response = self.get_response(request)
        return self._sign_response(response)

    def _is_exempt(self, path):
        return any(path.startswith(exempt) or path == exempt.rstrip('/') for exempt in self.EXEMPT_PATHS)

    def _sign_response(self, response):
        try:
            timestamp = str(int(time.time()))
            response_body = response.content.decode('utf-8') if response.content else ''
            message = f"RESPONSE|{response_body}|{timestamp}"
            signature = hmac.new(
                self.signing_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            response['X-Response-Timestamp'] = timestamp
            response['X-Response-Signature'] = signature
        except Exception as e:
            logger.error(f"Failed to sign response: {e}")
        return response


def generate_request_signature(method, path, body, timestamp, signing_key):
    """Generate request signature for API Service client."""
    message = f"{method}|{path}|{body}|{timestamp}"
    return hmac.new(signing_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def verify_response_signature(response_body, signature, timestamp, signing_key):
    """Verify response signature."""
    message = f"RESPONSE|{response_body}|{timestamp}"
    expected = hmac.new(signing_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

