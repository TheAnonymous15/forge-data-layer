# -*- coding: utf-8 -*-
"""
Data Layer - Authentication Module
==================================
Secure access to Data Layer documentation and health dashboards.
Uses database-backed user authentication.
"""
import secrets
import logging
from functools import wraps
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

logger = logging.getLogger('data_layer.auth')


def get_user_model():
    """Get the DataLayerUser model lazily to avoid circular imports."""
    from users.service_models import DataLayerUser
    return DataLayerUser


def verify_password(username: str, password: str) -> bool:
    """Verify username and password against database."""
    try:
        User = get_user_model()
        user = User.objects.filter(username=username.lower(), status='active').first()
        if user and user.check_password(password):
            return True
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def get_user(username: str) -> dict:
    """Get user information from database."""
    try:
        User = get_user_model()
        user = User.objects.filter(username=username.lower()).first()
        if user:
            return {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'name': user.full_name,
                'organization': user.organization,
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None


def is_authenticated(request) -> bool:
    """Check if the current request is authenticated."""
    return request.session.get('data_layer_authenticated', False)


def get_current_user(request) -> dict:
    """Get the current authenticated user."""
    if not is_authenticated(request):
        return None
    return {
        'id': request.session.get('data_layer_user_id'),
        'username': request.session.get('data_layer_username'),
        'role': request.session.get('data_layer_role'),
        'name': request.session.get('data_layer_name'),
    }


def login_user(request, username: str):
    """Log in a user by setting session variables."""
    try:
        User = get_user_model()
        user = User.objects.filter(username=username.lower()).first()
        if user:
            # Update login stats
            user.update_login()

            # Set session
            request.session['data_layer_authenticated'] = True
            request.session['data_layer_user_id'] = str(user.id)
            request.session['data_layer_username'] = user.username
            request.session['data_layer_role'] = user.role
            request.session['data_layer_name'] = user.full_name
            request.session['data_layer_csrf'] = secrets.token_urlsafe(32)
            return True
        return False
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        return False


def logout_user(request):
    """Log out the current user."""
    keys_to_remove = [
        'data_layer_authenticated',
        'data_layer_user_id',
        'data_layer_username',
        'data_layer_role',
        'data_layer_name',
        'data_layer_csrf',
    ]
    for key in keys_to_remove:
        request.session.pop(key, None)


def require_auth(view_func):
    """Decorator to require authentication for a view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request):
            # Store the original URL for redirect after login
            request.session['data_layer_next'] = request.get_full_path()
            return redirect('data-login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_role(allowed_roles):
    """Decorator to require specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not is_authenticated(request):
                request.session['data_layer_next'] = request.get_full_path()
                return redirect('data-login')

            user_role = request.session.get('data_layer_role')
            if user_role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('docs')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

