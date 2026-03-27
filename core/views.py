# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Core Views
=========================================
Documentation UI and health check views
"""
import logging
import json
from datetime import datetime

from django.conf import settings
from django.shortcuts import render, redirect
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .auth import (
    verify_password, login_user, logout_user,
    require_auth, get_current_user, is_authenticated, get_user
)

logger = logging.getLogger('data_layer.core')


# =============================================================================
# Authentication Views
# =============================================================================

@require_http_methods(["GET", "POST"])
def data_login(request):
    """Login page for Data Layer access."""
    # If already authenticated, redirect to docs
    if is_authenticated(request):
        next_url = request.session.pop('data_layer_next', '/docs/')
        return redirect(next_url)

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if verify_password(username, password):
            login_user(request, username)
            logger.info(f"Data Layer login successful for user: {username}")
            next_url = request.POST.get('next') or request.session.pop('data_layer_next', '/docs/')
            return redirect(next_url)
        else:
            error = "Invalid username or password"
            logger.warning(f"Data Layer login failed for user: {username}")

    return render(request, 'core/auth/login.html', {
        'error': error,
        'next': request.GET.get('next', ''),
    })


def data_logout(request):
    """Logout from Data Layer."""
    logout_user(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('data-login')


# =============================================================================
# AJAX Authentication Endpoints (for frontend login form)
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def ajax_login(request):
    """
    AJAX login endpoint for Data Layer.
    Authenticates user and sets up session.
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({
                'success': False,
                'error': 'Username and password are required'
            }, status=400)

        # Import the model
        from data_layer.models import DataLayerUser
        from django.db.models import Q

        # Find user
        try:
            user = DataLayerUser.objects.get(
                Q(username=username) | Q(email=username)
            )
        except DataLayerUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=401)

        # Check password
        if not user.check_password(password):
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials'
            }, status=401)

        # Check status
        if user.status != 'active':
            return JsonResponse({
                'success': False,
                'error': f'Account is {user.status}'
            }, status=403)

        # Check if default password
        if user.is_default_password:
            return JsonResponse({
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

        # Set up session
        request.session['data_layer_authenticated'] = True
        request.session['data_layer_user_id'] = str(user.id)
        request.session['data_layer_username'] = user.username
        request.session['data_layer_role'] = user.role
        request.session['data_layer_name'] = user.full_name

        # Update login stats
        user.update_login()

        logger.info(f"Data Layer AJAX login successful for user: {username}")

        # Determine redirect URL
        redirect_url = '/docs/'
        if user.role == 'admin':
            redirect_url = '/admin/dashboard/'

        return JsonResponse({
            'success': True,
            'requires_password_change': False,
            'redirect_url': redirect_url,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format'
        }, status=400)
    except Exception as e:
        logger.error(f"Data Layer AJAX login error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ajax_change_password(request):
    """
    AJAX password change endpoint for Data Layer.
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip().lower()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([username, current_password, new_password, confirm_password]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required'
            }, status=400)

        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'New passwords do not match'
            }, status=400)

        if len(new_password) < 8:
            return JsonResponse({
                'success': False,
                'error': 'Password must be at least 8 characters'
            }, status=400)

        # Import model
        from data_layer.models import DataLayerUser
        from django.db.models import Q

        # Find user
        try:
            user = DataLayerUser.objects.get(
                Q(username=username) | Q(email=username)
            )
        except DataLayerUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)

        # Verify current password
        if not user.check_password(current_password):
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect'
            }, status=401)

        # Update password
        user.set_password(new_password)
        user.is_default_password = False
        user.save()

        logger.info(f"Data Layer password changed for user: {username}")

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format'
        }, status=400)
    except Exception as e:
        logger.error(f"Data Layer password change error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


# =============================================================================
# Protected Views (require authentication)
# =============================================================================

@require_auth
def docs_ui(request):
    """Render the Data Layer documentation UI - requires authentication."""
    context = {
        'title': 'Data Layer Documentation',
        'version': '1.0.0',
        'base_url': request.build_absolute_uri('/api/v1/'),
        'timestamp': datetime.now().isoformat(),
        'user': get_current_user(request),
    }
    return render(request, 'core/docs/index.html', context)


@require_auth
def health_ui(request):
    """Render the Data Layer health monitoring UI - requires authentication."""
    context = {
        'title': 'Data Layer Health',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'user': get_current_user(request),
    }
    return render(request, 'core/health.html', context)


# =============================================================================
# API Endpoints (public health check)
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    # Check database connectivity
    db_status = 'healthy'
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    return Response({
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'service': 'data_layer',
        'version': '1.0.0',
        'database': db_status,
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'users': '/api/v1/users/',
            'profiles': '/api/v1/profiles/',
            'organizations': '/api/v1/organizations/',
            'opportunities': '/api/v1/opportunities/',
            'applications': '/api/v1/applications/',
            'media': '/api/v1/media/',
            'tokens': '/api/v1/tokens/',
            'audit': '/api/v1/audit/',
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_stats(request):
    """Return API statistics for the docs UI."""
    from users.models import User
    from profiles.models import TalentProfile
    from organizations.models import Organization
    from applications.models import Application
    from media.models import Document, Image

    try:
        stats = {
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
            },
            'profiles': {
                'total': TalentProfile.objects.count(),
            },
            'organizations': {
                'total': Organization.objects.count(),
            },
            'applications': {
                'total': Application.objects.count(),
            },
            'media': {
                'documents': Document.objects.count(),
                'images': Image.objects.count(),
            }
        }
    except Exception as e:
        stats = {'error': str(e)}

    return Response({
        'success': True,
        'stats': stats,
        'timestamp': datetime.now().isoformat(),
    })
