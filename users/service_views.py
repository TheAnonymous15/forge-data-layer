# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Service Authentication Views
=================================================
API endpoints for authenticating API Service and Data Layer users.
"""
import logging
import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .service_models import APIServiceUser, DataLayerUser, ServiceAccessRequest

logger = logging.getLogger('data_layer.service_auth')


# =============================================================================
# Helper Functions
# =============================================================================

def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


# =============================================================================
# API Service Authentication
# =============================================================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_service_login(request):
    """
    Authenticate API Service user.

    POST /api/v1/service-auth/api-service/login/
    {
        "username": "admin",
        "password": "secret"
    }
    """
    try:
        data = request.data
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')

        if not username or not password:
            return Response({
                'success': False,
                'error': 'Username and password are required',
            }, status=400)

        try:
            user = APIServiceUser.objects.get(username=username)
        except APIServiceUser.DoesNotExist:
            logger.warning(f"API Service login failed: user '{username}' not found")
            return Response({
                'success': False,
                'error': 'Invalid credentials',
            }, status=401)

        if user.status != 'active':
            logger.warning(f"API Service login failed: user '{username}' is {user.status}")
            return Response({
                'success': False,
                'error': 'Account is not active',
            }, status=403)

        if not user.check_password(password):
            logger.warning(f"API Service login failed: invalid password for '{username}'")
            return Response({
                'success': False,
                'error': 'Invalid credentials',
            }, status=401)

        # Update login info
        user.update_login()

        logger.info(f"API Service login successful for '{username}'")
        return Response({
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'organization': user.organization,
            }
        })

    except Exception as e:
        logger.error(f"API Service login error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_service_verify(request):
    """
    Verify API Service user session/token.

    POST /api/v1/service-auth/api-service/verify/
    {
        "user_id": "uuid",
        "session_token": "..."
    }
    """
    try:
        data = request.data
        user_id = data.get('user_id')

        if not user_id:
            return Response({
                'valid': False,
                'error': 'User ID required',
            }, status=400)

        try:
            user = APIServiceUser.objects.get(id=user_id, status='active')
            return Response({
                'valid': True,
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'role': user.role,
                }
            })
        except APIServiceUser.DoesNotExist:
            return Response({
                'valid': False,
                'error': 'User not found or inactive',
            }, status=401)

    except Exception as e:
        logger.error(f"API Service verify error: {e}")
        return Response({
            'valid': False,
            'error': 'Internal server error',
        }, status=500)


# =============================================================================
# Data Layer Authentication
# =============================================================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def data_layer_login(request):
    """
    Authenticate Data Layer user.

    POST /api/v1/service-auth/data-layer/login/
    {
        "username": "admin",
        "password": "secret"
    }
    """
    try:
        data = request.data
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')

        if not username or not password:
            return Response({
                'success': False,
                'error': 'Username and password are required',
            }, status=400)

        try:
            user = DataLayerUser.objects.get(username=username)
        except DataLayerUser.DoesNotExist:
            logger.warning(f"Data Layer login failed: user '{username}' not found")
            return Response({
                'success': False,
                'error': 'Invalid credentials',
            }, status=401)

        if user.status != 'active':
            logger.warning(f"Data Layer login failed: user '{username}' is {user.status}")
            return Response({
                'success': False,
                'error': 'Account is not active',
            }, status=403)

        if not user.check_password(password):
            logger.warning(f"Data Layer login failed: invalid password for '{username}'")
            return Response({
                'success': False,
                'error': 'Invalid credentials',
            }, status=401)

        # Update login info
        user.update_login()

        logger.info(f"Data Layer login successful for '{username}'")
        return Response({
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'organization': user.organization,
            }
        })

    except Exception as e:
        logger.error(f"Data Layer login error: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def data_layer_verify(request):
    """
    Verify Data Layer user session/token.

    POST /api/v1/service-auth/data-layer/verify/
    {
        "user_id": "uuid"
    }
    """
    try:
        data = request.data
        user_id = data.get('user_id')

        if not user_id:
            return Response({
                'valid': False,
                'error': 'User ID required',
            }, status=400)

        try:
            user = DataLayerUser.objects.get(id=user_id, status='active')
            return Response({
                'valid': True,
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'role': user.role,
                }
            })
        except DataLayerUser.DoesNotExist:
            return Response({
                'valid': False,
                'error': 'User not found or inactive',
            }, status=401)

    except Exception as e:
        logger.error(f"Data Layer verify error: {e}")
        return Response({
            'valid': False,
            'error': 'Internal server error',
        }, status=500)


# =============================================================================
# Access Requests
# =============================================================================

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def create_access_request(request):
    """
    Submit an access request for API Service or Data Layer.

    POST /api/v1/service-auth/access-request/
    {
        "full_name": "John Doe",
        "email": "john@example.com",
        "organization": "Company",
        "requested_role": "developer",
        "reason": "Need access for development",
        "service_type": "api_service" or "data_layer"
    }

    Returns:
        - success: True if access request was created
        - request_id: UUID of the created request
        - notification_sent: True if confirmation email was sent
        - notification_error: Error message if email failed (optional)
    """
    try:
        data = request.data

        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip().lower()
        organization = data.get('organization', '').strip()
        requested_role = data.get('requested_role', 'viewer')
        reason = data.get('reason', '').strip()
        service_type = data.get('service_type', 'api_service')

        if not full_name or not email:
            return Response({
                'success': False,
                'error': 'Full name and email are required',
            }, status=400)

        if not reason:
            return Response({
                'success': False,
                'error': 'Please explain why you need access',
            }, status=400)

        # Check for existing pending request
        existing = ServiceAccessRequest.objects.filter(
            email=email,
            service_type=service_type,
            status='pending'
        ).exists()

        if existing:
            return Response({
                'success': False,
                'error': 'You already have a pending request',
            }, status=400)

        # Create request
        access_request = ServiceAccessRequest.objects.create(
            full_name=full_name,
            email=email,
            organization=organization,
            requested_role=requested_role,
            reason=reason,
            service_type=service_type,
            ip_address=get_client_ip(request),
        )

        logger.info(f"Access request created: {email} for {service_type}")

        # Send confirmation email via internal Communications service
        notification_sent = False
        notification_error = None

        try:
            from communications.services import send_access_request_confirmation
            email_result = send_access_request_confirmation(
                full_name=full_name,
                email=email,
                service_type=service_type,
                request_id=str(access_request.id)
            )
            notification_sent = email_result.get('success', False)
            if not notification_sent:
                notification_error = email_result.get('error', 'Unknown email error')
                logger.warning(f"Failed to send confirmation email to {email}: {notification_error}")
        except Exception as email_exc:
            notification_error = str(email_exc)
            logger.error(f"Exception sending confirmation email to {email}: {email_exc}")

        return Response({
            'success': True,
            'message': 'Your access request has been submitted. You will be notified by email once reviewed.',
            'request_id': str(access_request.id),
            'notification_sent': notification_sent,
            'notification_error': notification_error,
        })

    except Exception as e:
        logger.error(f"Access request error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to submit request',
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])  # Should require admin auth in production
def list_access_requests(request):
    """
    List all pending access requests.
    """
    try:
        status_filter = request.query_params.get('status', 'pending')
        service_filter = request.query_params.get('service')

        queryset = ServiceAccessRequest.objects.all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if service_filter:
            queryset = queryset.filter(service_type=service_filter)

        queryset = queryset.order_by('-created_at')[:50]

        requests_data = [{
            'id': str(r.id),
            'full_name': r.full_name,
            'email': r.email,
            'organization': r.organization,
            'requested_role': r.requested_role,
            'service_type': r.service_type,
            'reason': r.reason,
            'status': r.status,
            'created_at': r.created_at.isoformat(),
        } for r in queryset]

        return Response({
            'success': True,
            'requests': requests_data,
            'count': len(requests_data),
        })

    except Exception as e:
        logger.error(f"List access requests error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to list requests',
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Should require admin auth in production
def approve_access_request(request, request_id):
    """
    Approve an access request and create user account.
    """
    try:
        try:
            access_request = ServiceAccessRequest.objects.get(id=request_id)
        except ServiceAccessRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Request not found',
            }, status=404)

        if access_request.status != 'pending':
            return Response({
                'success': False,
                'error': f'Request already {access_request.status}',
            }, status=400)

        # Generate username from email
        username = access_request.email.split('@')[0].lower()

        # Generate temporary password
        import secrets
        temp_password = secrets.token_urlsafe(12)

        # Create user based on service type
        if access_request.service_type == 'api_service':
            UserModel = APIServiceUser
        else:
            UserModel = DataLayerUser

        # Check if username exists
        if UserModel.objects.filter(username=username).exists():
            username = f"{username}_{secrets.token_hex(3)}"

        user = UserModel.objects.create_user(
            username=username,
            email=access_request.email,
            password=temp_password,
            full_name=access_request.full_name,
            organization=access_request.organization,
            role=access_request.requested_role,
        )

        # Update request status
        access_request.status = 'approved'
        access_request.reviewed_at = timezone.now()
        access_request.save()

        logger.info(f"Access request approved: {access_request.email}")

        # Send approval email with credentials via internal Communications service
        notification_sent = False
        notification_error = None

        try:
            from communications.services import send_access_request_approved
            email_result = send_access_request_approved(
                full_name=access_request.full_name,
                email=access_request.email,
                service_type=access_request.service_type,
                username=username,
                temp_password=temp_password
            )
            notification_sent = email_result.get('success', False)
            if not notification_sent:
                notification_error = email_result.get('error', 'Unknown email error')
                logger.warning(f"Failed to send approval email to {access_request.email}: {notification_error}")
        except Exception as email_exc:
            notification_error = str(email_exc)
            logger.error(f"Exception sending approval email to {access_request.email}: {email_exc}")

        return Response({
            'success': True,
            'message': 'Request approved and user created',
            'user': {
                'id': str(user.id),
                'username': user.username,
                'temp_password': temp_password,  # Only show once
            },
            'notification_sent': notification_sent,
            'notification_error': notification_error,
        })

    except Exception as e:
        logger.error(f"Approve request error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to approve request',
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Should require admin auth in production
def reject_access_request(request, request_id):
    """
    Reject an access request.
    """
    try:
        rejection_reason = request.data.get('reason', '').strip()

        try:
            access_request = ServiceAccessRequest.objects.get(id=request_id)
        except ServiceAccessRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Request not found',
            }, status=404)

        if access_request.status != 'pending':
            return Response({
                'success': False,
                'error': f'Request already {access_request.status}',
            }, status=400)

        access_request.status = 'rejected'
        access_request.reviewed_at = timezone.now()
        access_request.save()

        logger.info(f"Access request rejected: {access_request.email}")

        # Send rejection email via internal Communications service
        notification_sent = False
        notification_error = None

        try:
            from communications.services import send_access_request_rejected
            email_result = send_access_request_rejected(
                full_name=access_request.full_name,
                email=access_request.email,
                service_type=access_request.service_type,
                rejection_reason=rejection_reason
            )
            notification_sent = email_result.get('success', False)
            if not notification_sent:
                notification_error = email_result.get('error', 'Unknown email error')
                logger.warning(f"Failed to send rejection email to {access_request.email}: {notification_error}")
        except Exception as email_exc:
            notification_error = str(email_exc)
            logger.error(f"Exception sending rejection email to {access_request.email}: {email_exc}")

        return Response({
            'success': True,
            'message': 'Request rejected',
            'notification_sent': notification_sent,
            'notification_error': notification_error,
        })

    except Exception as e:
        logger.error(f"Reject request error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to reject request',
        }, status=500)


# =============================================================================
# User Management
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])  # Should require admin auth in production
def list_api_service_users(request):
    """List all API Service users."""
    try:
        users = APIServiceUser.objects.all().order_by('-created_at')[:100]
        users_data = [{
            'id': str(u.id),
            'username': u.username,
            'email': u.email,
            'full_name': u.full_name,
            'role': u.role,
            'status': u.status,
            'organization': u.organization,
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'login_count': u.login_count,
            'created_at': u.created_at.isoformat(),
        } for u in users]

        return Response({
            'success': True,
            'users': users_data,
            'count': len(users_data),
        })

    except Exception as e:
        logger.error(f"List API users error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to list users',
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])  # Should require admin auth in production
def list_data_layer_users(request):
    """List all Data Layer users."""
    try:
        users = DataLayerUser.objects.all().order_by('-created_at')[:100]
        users_data = [{
            'id': str(u.id),
            'username': u.username,
            'email': u.email,
            'full_name': u.full_name,
            'role': u.role,
            'status': u.status,
            'organization': u.organization,
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'login_count': u.login_count,
            'created_at': u.created_at.isoformat(),
        } for u in users]

        return Response({
            'success': True,
            'users': users_data,
            'count': len(users_data),
        })

    except Exception as e:
        logger.error(f"List Data Layer users error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to list users',
        }, status=500)


@csrf_exempt
@api_view(['POST', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Should require admin auth in production
def manage_api_service_user(request, user_id):
    """Manage a single API Service user."""
    try:
        try:
            user = APIServiceUser.objects.get(id=user_id)
        except APIServiceUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found',
            }, status=404)

        if request.method == 'DELETE':
            user.delete()
            return Response({'success': True, 'message': 'User deleted'})

        # PUT/POST - Update user
        data = request.data

        if 'status' in data:
            user.status = data['status']
        if 'role' in data:
            user.role = data['role']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'organization' in data:
            user.organization = data['organization']
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        user.save()

        return Response({
            'success': True,
            'message': 'User updated',
            'user': {
                'id': str(user.id),
                'username': user.username,
                'role': user.role,
                'status': user.status,
            }
        })

    except Exception as e:
        logger.error(f"Manage API user error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to manage user',
        }, status=500)


@csrf_exempt
@api_view(['POST', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Should require admin auth in production
def manage_data_layer_user(request, user_id):
    """Manage a single Data Layer user."""
    try:
        try:
            user = DataLayerUser.objects.get(id=user_id)
        except DataLayerUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found',
            }, status=404)

        if request.method == 'DELETE':
            user.delete()
            return Response({'success': True, 'message': 'User deleted'})

        # PUT/POST - Update user
        data = request.data

        if 'status' in data:
            user.status = data['status']
        if 'role' in data:
            user.role = data['role']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'organization' in data:
            user.organization = data['organization']
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        user.save()

        return Response({
            'success': True,
            'message': 'User updated',
            'user': {
                'id': str(user.id),
                'username': user.username,
                'role': user.role,
                'status': user.status,
            }
        })

    except Exception as e:
        logger.error(f"Manage Data Layer user error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to manage user',
        }, status=500)

