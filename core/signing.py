# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Signing Module
==============================================
Cryptographic signing and verification for secure API Service ↔ Data Layer communication.

Flow:
- API Service signs requests → Data Layer verifies
- Data Layer signs responses → API Service verifies
"""
import hmac
import hashlib
import json
import time
import base64
import logging
import secrets
from typing import Dict, Any, Optional, Tuple
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger('data_layer.signing')

# Shared secret between API Service and Data Layer
# In production, this should be in environment variables
API_DATA_LAYER_SECRET = getattr(settings, 'API_DATA_LAYER_SECRET', 'ff_api_data_layer_secret_2026_secure')

# Signature validity window (5 minutes)
TIMESTAMP_TOLERANCE = 300

# Nonce cache TTL (10 minutes)
NONCE_TTL = 600


class SigningError(Exception):
    """Exception raised for signing/verification errors."""
    pass


def _get_body_hash(body: bytes) -> str:
    """Generate SHA256 hash of request body."""
    if not body:
        return hashlib.sha256(b'').hexdigest()
    return hashlib.sha256(body).hexdigest()


def _create_canonical_string(
    timestamp: str,
    method: str,
    path: str,
    body_hash: str,
    nonce: str
) -> str:
    """Create canonical string for signing."""
    return f"{timestamp}\n{method.upper()}\n{path}\n{body_hash}\n{nonce}"


def verify_api_service_request(
    signature: str,
    timestamp: str,
    nonce: str,
    method: str,
    path: str,
    body: bytes = b''
) -> Tuple[bool, Optional[str]]:
    """
    Verify a signed request from API Service.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check timestamp freshness
    try:
        request_time = int(timestamp)
        current_time = int(time.time())
        
        if abs(current_time - request_time) > TIMESTAMP_TOLERANCE:
            return False, "Request timestamp expired or invalid"
    except (ValueError, TypeError):
        return False, "Invalid timestamp format"
    
    # Check nonce hasn't been used (replay protection)
    nonce_key = f"dl_nonce:{nonce}"
    if cache.get(nonce_key):
        return False, "Duplicate request detected (nonce reuse)"
    
    # Store nonce to prevent replay
    cache.set(nonce_key, True, NONCE_TTL)
    
    # Recreate canonical string
    body_hash = _get_body_hash(body)
    canonical = _create_canonical_string(timestamp, method, path, body_hash, nonce)
    
    # Calculate expected signature
    expected_sig = hmac.new(
        API_DATA_LAYER_SECRET.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    expected_b64 = base64.b64encode(expected_sig).decode('utf-8')
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(signature, expected_b64):
        logger.warning("Invalid signature from API Service")
        return False, "Invalid signature"
    
    logger.debug("Valid API Service signature verified")
    return True, None


def sign_response(body: bytes, request_nonce: str = '') -> Dict[str, str]:
    """
    Sign a response to send back to API Service.
    
    Args:
        body: Response body bytes
        request_nonce: Original request nonce (for correlation)
    
    Returns:
        Dict with signature headers
    """
    timestamp = str(int(time.time()))
    response_id = secrets.token_hex(16)
    
    # Include request nonce in signature for request-response binding
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = f"{timestamp}\n{body_hash}\n{request_nonce}\n{response_id}"
    
    signature = hmac.new(
        API_DATA_LAYER_SECRET.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    return {
        'X-Response-Signature': signature_b64,
        'X-Response-Timestamp': timestamp,
        'X-Response-ID': response_id,
    }


def create_signed_json_response(data: Dict[str, Any], request_nonce: str = '') -> Dict[str, Any]:
    """
    Create a signed JSON response payload.
    
    Args:
        data: Response data dictionary
        request_nonce: Original request nonce
    
    Returns:
        Signed payload with signature metadata
    """
    timestamp = str(int(time.time()))
    response_id = secrets.token_hex(16)
    
    # Serialize data deterministically
    body = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    body_hash = hashlib.sha256(body).hexdigest()
    
    canonical = f"{timestamp}\n{body_hash}\n{request_nonce}\n{response_id}"
    
    signature = hmac.new(
        API_DATA_LAYER_SECRET.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return {
        **data,
        '_signature': {
            'sig': base64.b64encode(signature).decode('utf-8'),
            'ts': timestamp,
            'id': response_id,
            'nonce': request_nonce,
        }
    }


def require_signed_request(view_func):
    """
    Decorator to require signed requests from API Service.
    Rejects any unsigned or incorrectly signed requests.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Extract signature headers
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')
        nonce = request.META.get('HTTP_X_NONCE')
        client_id = request.META.get('HTTP_X_CLIENT_ID')
        
        # In development mode, allow unsigned requests with warning
        if settings.DEBUG and not signature:
            logger.warning("Unsigned request received in development mode")
            return view_func(request, *args, **kwargs)
        
        if not all([signature, timestamp, nonce]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required signature headers (X-Signature, X-Timestamp, X-Nonce)',
                'code': 'SIGNATURE_MISSING'
            }, status=401)
        
        # Verify signature
        is_valid, error = verify_api_service_request(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            method=request.method,
            path=request.path,
            body=request.body
        )
        
        if not is_valid:
            logger.warning(f"Request signature verification failed: {error}")
            return JsonResponse({
                'success': False,
                'error': f'Request signature verification failed: {error}',
                'code': 'SIGNATURE_INVALID'
            }, status=401)
        
        # Store nonce for response signing
        request.request_nonce = nonce
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class SignedJsonResponse(JsonResponse):
    """
    JsonResponse that automatically signs the response.
    """
    def __init__(self, data, request_nonce='', **kwargs):
        # Sign the response data
        signed_data = create_signed_json_response(data, request_nonce)
        super().__init__(signed_data, **kwargs)

