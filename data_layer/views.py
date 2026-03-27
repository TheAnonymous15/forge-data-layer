# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Views
====================================
Handles Data Layer user management and access request operations.
"""
import logging
import secrets
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import DataLayerUser, DataLayerAccessRequest, DataLayerAuditLog

logger = logging.getLogger('data_layer')


# =============================================================================
# Helper Functions
# =============================================================================

def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(user_id, username, action, resource_type, resource_id=None, details=None, request=None):
    """Create an audit log entry."""
    try:
        DataLayerAuditLog.objects.create(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else None,
        )
    except Exception:
        pass


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


# =============================================================================
# Data Layer Authentication
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def data_layer_login(request):
    """Authenticate a Data Layer user."""
    try:
        data = request.data
        username = data.get('username', '').lower().strip()
        password = data.get('password', '')

        if not username or not password:
            return Response({
                'success': False,
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = DataLayerUser.objects.get(
                Q(username=username) | Q(email=username)
            )
        except DataLayerUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if user.status != DataLayerUser.Status.ACTIVE:
            return Response({
                'success': False,
                'error': f'Account is {user.status}'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if user needs to change default password
        if user.is_default_password:
            return Response({
                'success': True,
                'requires_password_change': True,
                'message': 'Please change your default password before proceeding',
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                }
            })

        # Update login info
        user.update_login()

        # Log the login
        log_audit(user.id, user.username, 'login', 'user', user.id, None, request)

        # Generate token
        token = generate_token()

        # Determine redirect URL based on role
        redirect_url = '/docs/'  # Default for Data Layer
        if user.role == 'admin':
            redirect_url = '/admin/dashboard/'
        elif user.role == 'developer':
            redirect_url = '/docs/'
        elif user.role == 'analyst':
            redirect_url = '/analytics/'

        return Response({
            'success': True,
            'requires_password_change': False,
            'redirect_url': redirect_url,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'organization': user.organization,
            },
            'token': token,
            'expires_in': 3600
        })

    except Exception as e:
        logger.error(f"Data Layer login error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def change_password(request):
    """Change password for a Data Layer user (especially for default password change)."""
    try:
        data = request.data
        username = data.get('username', '').lower().strip()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        # Validation
        if not username or not current_password or not new_password:
            return Response({
                'success': False,
                'error': 'Username, current password and new password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                'success': False,
                'error': 'New password and confirmation do not match'
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({
                'success': False,
                'error': 'Password must be at least 8 characters long'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find user
        try:
            user = DataLayerUser.objects.get(
                Q(username=username) | Q(email=username)
            )
        except DataLayerUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify current password
        if not user.check_password(current_password):
            return Response({
                'success': False,
                'error': 'Current password is incorrect'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Set new password and clear default password flag
        user.set_password(new_password)
        user.is_default_password = False
        user.save(update_fields=['password_hash', 'is_default_password', 'updated_at'])

        # Log the password change
        log_audit(user.id, user.username, 'password_change', 'user', user.id, {'reason': 'user_initiated'}, request)

        # Send password changed notification email
        from communications.services import send_password_changed_email
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        email_result = send_password_changed_email(
            to_email=user.email,
            full_name=user.full_name,
            service_type='data_layer',
            ip_address=ip_address,
            user_agent=user_agent
        )

        logger.info(f"Data Layer password changed: {user.username}")

        return Response({
            'success': True,
            'message': 'Password changed successfully',
            'notification_sent': email_result.get('success', False)
        })

    except Exception as e:
        logger.error(f"Change password error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def data_layer_logout(request):
    """Logout a Data Layer user."""
    return Response({'success': True, 'message': 'Logged out successfully'})


# =============================================================================
# Access Request Operations
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def create_access_request(request):
    """Create a new Data Layer access request."""
    try:
        data = request.data

        required_fields = ['full_name', 'email', 'reason']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'success': False,
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        email = data['email'].lower().strip()

        # Check for existing pending request
        existing = DataLayerAccessRequest.objects.filter(
            email=email,
            status=DataLayerAccessRequest.Status.PENDING
        ).exists()

        if existing:
            return Response({
                'success': False,
                'error': 'You already have a pending request'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        if DataLayerUser.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': 'An account with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create access request
        access_request = DataLayerAccessRequest.objects.create(
            full_name=data['full_name'],
            email=email,
            phone=data.get('phone'),
            organization=data.get('organization'),
            job_title=data.get('job_title'),
            requested_role=data.get('requested_role', 'readonly'),
            reason=data['reason'],
            intended_use=data.get('intended_use'),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        logger.info(f"Data Layer access request created: {access_request.email}")

        # Send confirmation email
        notification_sent = False
        try:
            from communications.services import send_access_request_confirmation
            email_result = send_access_request_confirmation(
                full_name=access_request.full_name,
                email=access_request.email,
                service_type='data_layer',
                request_id=str(access_request.id)
            )
            notification_sent = email_result.get('success', False)
        except Exception as e:
            logger.warning(f"Failed to send confirmation email: {e}")

        return Response({
            'success': True,
            'message': 'Access request submitted successfully',
            'request_id': str(access_request.id),
            'notification_sent': notification_sent
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Create access request error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_access_requests(request):
    """List all Data Layer access requests with pagination and filtering."""
    try:
        queryset = DataLayerAccessRequest.objects.all()

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(organization__icontains=search)
            )

        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        requests_data = [{
            'id': str(req.id),
            'requested_role': req.requested_role,
            'full_name': req.full_name,
            'email': req.email,
            'organization': req.organization,
            'reason': req.reason,
            'status': req.status,
            'created_at': req.created_at.isoformat(),
            'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
        } for req in page_obj]

        return Response({
            'success': True,
            'requests': requests_data,
            'total': paginator.count,
            'page': page,
            'per_page': per_page,
            'total_pages': paginator.num_pages
        })

    except Exception as e:
        logger.error(f"List access requests error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_access_request(request, request_id):
    """Get a specific Data Layer access request."""
    try:
        access_request = DataLayerAccessRequest.objects.get(id=request_id)

        return Response({
            'success': True,
            'request': {
                'id': str(access_request.id),
                'requested_role': access_request.requested_role,
                'full_name': access_request.full_name,
                'email': access_request.email,
                'phone': access_request.phone,
                'organization': access_request.organization,
                'job_title': access_request.job_title,
                'reason': access_request.reason,
                'intended_use': access_request.intended_use,
                'status': access_request.status,
                'reviewed_by': access_request.reviewed_by,
                'reviewed_at': access_request.reviewed_at.isoformat() if access_request.reviewed_at else None,
                'admin_notes': access_request.admin_notes,
                'rejection_reason': access_request.rejection_reason,
                'created_at': access_request.created_at.isoformat(),
            }
        })

    except DataLayerAccessRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Access request not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Get access request error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def approve_access_request(request, request_id):
    """Approve a Data Layer access request and create user account."""
    try:
        access_request = DataLayerAccessRequest.objects.get(id=request_id)

        if access_request.status != DataLayerAccessRequest.Status.PENDING:
            return Response({
                'success': False,
                'error': f'Request already {access_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use email as username
        username = access_request.email.lower()
        temp_password = secrets.token_urlsafe(12)

        # Check if user already exists
        if DataLayerUser.objects.filter(email=username).exists():
            return Response({
                'success': False,
                'error': 'An account with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create user with email as username and is_default_password=True
        user = DataLayerUser.objects.create_user(
            username=username,
            email=access_request.email,
            password=temp_password,
            full_name=access_request.full_name,
            organization=access_request.organization,
            role=access_request.requested_role,
        )
        # Set is_default_password flag
        user.is_default_password = True
        user.save(update_fields=['is_default_password'])

        # Update request status
        data = request.data
        access_request.status = DataLayerAccessRequest.Status.APPROVED
        access_request.reviewed_at = timezone.now()
        access_request.reviewed_by = data.get('admin_username', 'system')
        access_request.admin_notes = data.get('admin_notes')
        access_request.created_user_id = user.id
        access_request.created_username = username
        access_request.save()

        logger.info(f"Data Layer access request approved: {access_request.email}")

        # Send approval email with email as username
        notification_sent = False
        notification_error = None
        try:
            from communications.services import send_access_request_approved
            email_result = send_access_request_approved(
                full_name=access_request.full_name,
                email=access_request.email,
                service_type='data_layer',
                username=username,  # Using email as username
                temp_password=temp_password,
                login_url='http://localhost:9005/docs/'
            )
            notification_sent = email_result.get('success', False)
            if not notification_sent:
                notification_error = email_result.get('error')
        except Exception as e:
            notification_error = str(e)
            logger.warning(f"Failed to send approval email: {e}")

        return Response({
            'success': True,
            'message': 'Request approved and user created',
            'user': {
                'id': str(user.id),
                'username': username,
                'email': user.email,
                'temp_password': temp_password,
                'is_default_password': True,
            },
            'notification_sent': notification_sent,
            'notification_error': notification_error
        })

    except DataLayerAccessRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Access request not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Approve access request error: {e}")
        return Response({
            'success': False,
            'error': 'Failed to approve request'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reject_access_request(request, request_id):
    """Reject a Data Layer access request."""
    try:
        access_request = DataLayerAccessRequest.objects.get(id=request_id)

        if access_request.status != DataLayerAccessRequest.Status.PENDING:
            return Response({
                'success': False,
                'error': f'Request already {access_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        reason = data.get('reason', 'Request rejected by administrator')

        access_request.reject(
            admin_username=data.get('admin_username', 'system'),
            reason=reason
        )

        logger.info(f"Data Layer access request rejected: {access_request.email}")

        # Send rejection email
        notification_sent = False
        try:
            from communications.services import send_access_request_rejected
            email_result = send_access_request_rejected(
                full_name=access_request.full_name,
                email=access_request.email,
                service_type='data_layer',
                rejection_reason=reason
            )
            notification_sent = email_result.get('success', False)
        except Exception as e:
            logger.warning(f"Failed to send rejection email: {e}")

        return Response({
            'success': True,
            'message': 'Request rejected',
            'notification_sent': notification_sent
        })

    except DataLayerAccessRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Access request not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Reject access request error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# User Management
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def list_users(request):
    """List all Data Layer users."""
    try:
        queryset = DataLayerUser.objects.all()

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by role
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(full_name__icontains=search)
            )

        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        users_data = [{
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'organization': user.organization,
            'role': user.role,
            'status': user.status,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat(),
        } for user in page_obj]

        return Response({
            'success': True,
            'users': users_data,
            'total': paginator.count,
            'page': page,
            'per_page': per_page,
            'total_pages': paginator.num_pages
        })

    except Exception as e:
        logger.error(f"List users error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user(request, user_id):
    """Get a specific Data Layer user."""
    try:
        user = DataLayerUser.objects.get(id=user_id)

        return Response({
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'organization': user.organization,
                'role': user.role,
                'status': user.status,
                'login_count': user.login_count,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat(),
            }
        })

    except DataLayerUser.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Health Check
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Data Layer health check endpoint."""
    return Response({
        'success': True,
        'status': 'healthy',
        'service': 'data_layer',
        'timestamp': timezone.now().isoformat()
    })

