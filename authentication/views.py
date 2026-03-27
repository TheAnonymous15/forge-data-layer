# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Authentication Views
===================================================
Handles all authentication operations with actual database access.
"""
import logging
import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
    VerifyEmailSerializer,
    ResendVerificationSerializer,
    UserResponseSerializer,
)
from .models import User, LoginHistory, UserSession, EmailVerificationToken, PasswordResetToken

logger = logging.getLogger('data_layer.authentication')
User = get_user_model()


def get_tokens_for_user(user):
    """Generate JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'access_expires': int(refresh.access_token.lifetime.total_seconds()),
        'refresh_expires': int(refresh.lifetime.total_seconds()),
    }


def create_user_session(user, refresh_token, ip_address=None, user_agent=None):
    """Create a user session record."""
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Parse device info from user agent
    device_type = 'desktop'
    device_name = 'Unknown'
    if user_agent:
        ua_lower = user_agent.lower()
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            device_type = 'mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device_type = 'tablet'
        
        # Simple device name extraction
        if 'chrome' in ua_lower:
            device_name = 'Chrome Browser'
        elif 'firefox' in ua_lower:
            device_name = 'Firefox Browser'
        elif 'safari' in ua_lower:
            device_name = 'Safari Browser'
        elif 'edge' in ua_lower:
            device_name = 'Edge Browser'
    
    return UserSession.objects.create(
        user=user,
        token_hash=token_hash,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=timezone.now() + timedelta(days=7)
    )


def record_login_attempt(email, status_val, user=None, ip_address=None, user_agent=None, failure_reason=None):
    """Record a login attempt."""
    LoginHistory.objects.create(
        user=user,
        email=email,
        status=status_val,
        ip_address=ip_address,
        user_agent=user_agent,
        failure_reason=failure_reason
    )


# =============================================================================
# Registration
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user."""
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # Build phone number from code + number
        phone_number = None
        phone_code = data.get('phone_code', '').strip()
        phone = data.get('phone', '').strip()
        if phone_code and phone:
            phone_number = f"{phone_code}{phone}"
        elif phone:
            phone_number = phone
        
        # Check phone uniqueness if provided
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': {'phone': ['A user with this phone number already exists.']}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine consent flags (support both old and new field names)
        terms_accepted = data.get('terms_accepted') or data.get('consent_terms', False)
        privacy_accepted = data.get('privacy_accepted') or data.get('consent_data', False)
        age_confirmed = data.get('consent_age', False)
        
        # Get user role
        user_role = data.get('role', 'talent')
        
        # Create user
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_code=phone_code or None,
            phone_number=phone_number or None,
            role=user_role,
            country=data.get('country') or data.get('organization_country') or None,
            date_of_birth=data.get('date_of_birth') or None,
            gender=data.get('gender') or None,
            bio=data.get('bio') or None,
            education_level=data.get('education_level') or None,
            opportunity_types=data.get('opportunity_types', []),
            skills=data.get('skills', []),
            preferred_fields=data.get('preferred_fields', []),
            referral_source=data.get('referral_source') or None,
            consent_age_confirmed=age_confirmed,
            consent_data_processing=privacy_accepted,
            terms_accepted_at=timezone.now() if terms_accepted else None,
            privacy_accepted_at=timezone.now() if privacy_accepted else None,
            marketing_consent=data.get('marketing_consent', False),
            registration_ip=data.get('ip_address') or None,
            job_title=data.get('job_title') or None,
            consent_authorized=data.get('consent_authorized', False),
        )
        
        # Create Organization for employer/partner roles
        organization = None
        if user_role in ['employer', 'partner'] and data.get('organization_name'):
            from organizations.models import Organization
            from django.utils.text import slugify
            
            # Generate unique slug
            base_slug = slugify(data['organization_name'])
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            organization = Organization.objects.create(
                name=data['organization_name'],
                slug=slug,
                industry=data.get('organization_industry') or None,
                industry_other=data.get('organization_industry_other') or None,
                size=data.get('organization_size') or None,
                website=data.get('organization_website') or None,
                headquarters_country=data.get('organization_country') or None,
                interest_types=data.get('organization_interest_types', []),
                initial_message=data.get('organization_message') or None,
                owner=user,
            )
            
            # Link user to organization
            user.organization_id = organization.id
            user.save(update_fields=['organization_id'])
            
            logger.info(f"Organization created: {organization.name} for user {user.email}")
        
        # Create email verification token
        verification_token = EmailVerificationToken.create_for_user(user)
        
        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        # Create session
        create_user_session(
            user, 
            tokens['refresh'],
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )
        
        logger.info(f"New user registered: {user.email}")
        
        # Send verification email via communications service
        verification_email_sent = False
        try:
            from communications.services import send_registration_verification_email
            
            # Build verification URL
            base_url = getattr(settings, 'TALENT_PORTAL_URL', 'https://talent.forgeforthafrica.com')
            verification_url = f"{base_url}/verify-email?token={verification_token.token}"
            
            email_result = send_registration_verification_email(
                full_name=user.full_name,
                email=user.email,
                verification_url=verification_url,
                token=verification_token.token
            )
            verification_email_sent = email_result.get('success', False)
            if verification_email_sent:
                logger.info(f"Verification email sent to {user.email}")
            else:
                logger.warning(f"Failed to send verification email to {user.email}: {email_result.get('error')}")
        except Exception as email_exc:
            logger.error(f"Exception sending verification email to {user.email}: {email_exc}")
        
        # Build response data
        response_data = {
            'success': True,
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': UserResponseSerializer(user).data,
            'tokens': tokens,
            'verification_required': True,
            'verification_email_sent': verification_email_sent,
            'verification_token': verification_token.token,  # For development/testing - remove in production
        }
        
        # Include organization data for employer/partner
        if organization:
            response_data['organization'] = {
                'id': str(organization.id),
                'name': organization.name,
                'slug': organization.slug,
                'industry': organization.industry,
                'size': organization.size,
                'website': organization.website,
                'country': organization.headquarters_country,
                'interest_types': organization.interest_types,
                'verification_status': organization.verification_status,
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Registration failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Partner/Organization Registration
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def register_partner(request):
    """
    Register a new partner/organization.
    
    This is a dedicated endpoint for partner/employer registration that requires
    organization details and validates partner-specific fields.
    """
    from .serializers import PartnerRegisterSerializer
    
    serializer = PartnerRegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # Build phone number from code + number
        phone_number = None
        phone_code = data.get('phone_code', '').strip()
        phone = data.get('phone', '').strip()
        if phone_code and phone:
            phone_number = f"{phone_code}{phone}"
        elif phone:
            phone_number = phone
        
        # Check phone uniqueness if provided
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': {'phone': ['A user with this phone number already exists.']}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the organization first
        from organizations.models import Organization
        from django.utils.text import slugify
        
        # Generate unique slug
        base_slug = slugify(data['organization_name'])
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create user (contact person)
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_code=phone_code or None,
            phone_number=phone_number or None,
            role='employer',  # Partners are employers
            country=data.get('organization_country') or None,
            job_title=data.get('job_title') or None,
            consent_authorized=data.get('consent_authorized', False),
            consent_data_processing=data.get('consent_data', False),
            terms_accepted_at=timezone.now() if data.get('consent_terms') else None,
            privacy_accepted_at=timezone.now() if data.get('consent_data') else None,
            registration_ip=data.get('ip_address') or None,
        )
        
        # Create Organization
        organization = Organization.objects.create(
            name=data['organization_name'],
            slug=slug,
            industry=data.get('organization_industry') or None,
            industry_other=data.get('organization_industry_other') or None,
            size=data.get('organization_size') or None,
            website=data.get('organization_website') or None,
            headquarters_country=data.get('organization_country') or None,
            interest_types=data.get('organization_interest_types', []),
            initial_message=data.get('organization_message') or None,
            owner=user,
        )
        
        # Link user to organization
        user.organization_id = organization.id
        user.save(update_fields=['organization_id'])
        
        logger.info(f"Partner registered: {user.email} for organization: {organization.name}")
        
        # Create email verification token
        verification_token = EmailVerificationToken.create_for_user(user)
        
        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        # Create session
        create_user_session(
            user, 
            tokens['refresh'],
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )
        
        # Send verification email via communications service
        verification_email_sent = False
        try:
            from communications.services import send_registration_verification_email
            
            # Build verification URL for partner portal
            base_url = getattr(settings, 'PARTNER_PORTAL_URL', 'https://partners.forgeforthafrica.com')
            verification_url = f"{base_url}/verify-email?token={verification_token.token}"
            
            email_result = send_registration_verification_email(
                full_name=user.full_name,
                email=user.email,
                verification_url=verification_url,
                token=verification_token.token
            )
            verification_email_sent = email_result.get('success', False)
            if verification_email_sent:
                logger.info(f"Partner verification email sent to {user.email}")
            else:
                logger.warning(f"Failed to send partner verification email to {user.email}: {email_result.get('error')}")
        except Exception as email_exc:
            logger.error(f"Exception sending partner verification email to {user.email}: {email_exc}")
        
        return Response({
            'success': True,
            'message': 'Partner registration successful. Please check your email to verify your account.',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'job_title': user.job_title,
                'role': user.role,
                'is_verified': user.is_verified,
            },
            'organization': {
                'id': str(organization.id),
                'name': organization.name,
                'slug': organization.slug,
                'industry': organization.industry,
                'size': organization.size,
                'website': organization.website,
                'country': organization.headquarters_country,
                'interest_types': organization.interest_types,
                'verification_status': organization.verification_status,
            },
            'tokens': tokens,
            'verification_required': True,
            'verification_email_sent': verification_email_sent,
            'verification_token': verification_token.token,  # For development/testing
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Partner registration failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Partner registration failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Login
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Authenticate user and return tokens."""
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    email = data['email'].lower()
    password = data['password']
    ip_address = data.get('ip_address')
    user_agent = data.get('user_agent')
    
    # Check if user exists
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        record_login_attempt(email, 'failed', ip_address=ip_address, user_agent=user_agent, 
                           failure_reason='User not found')
        return Response({
            'success': False,
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if account is locked
    if user.is_locked():
        record_login_attempt(email, 'blocked', user=user, ip_address=ip_address, user_agent=user_agent,
                           failure_reason='Account locked')
        return Response({
            'success': False,
            'error': 'Account is temporarily locked. Please try again later.',
            'locked_until': user.locked_until.isoformat()
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if account is active
    if not user.is_active:
        record_login_attempt(email, 'failed', user=user, ip_address=ip_address, user_agent=user_agent,
                           failure_reason='Account inactive')
        return Response({
            'success': False,
            'error': 'Account is deactivated'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if email is verified
    if not user.is_verified:
        record_login_attempt(email, 'failed', user=user, ip_address=ip_address, user_agent=user_agent,
                           failure_reason='Email not verified')
        return Response({
            'success': False,
            'error': 'Please verify your email before logging in. Check your inbox for the verification link.',
            'code': 'EMAIL_NOT_VERIFIED',
            'email': user.email,
            'can_resend': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Verify password
    if not user.check_password(password):
        user.increment_failed_login()
        record_login_attempt(email, 'failed', user=user, ip_address=ip_address, user_agent=user_agent,
                           failure_reason='Invalid password')
        return Response({
            'success': False,
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        record_login_attempt(email, 'requires_2fa', user=user, ip_address=ip_address, user_agent=user_agent)
        return Response({
            'success': True,
            'requires_2fa': True,
            'user_id': str(user.id),
            'two_factor_method': user.two_factor_method
        }, status=status.HTTP_200_OK)
    
    # Reset failed login attempts
    user.reset_failed_login()
    
    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    
    # Generate tokens
    tokens = get_tokens_for_user(user)
    
    # Create session
    create_user_session(user, tokens['refresh'], ip_address=ip_address, user_agent=user_agent)
    
    # Record successful login
    record_login_attempt(email, 'success', user=user, ip_address=ip_address, user_agent=user_agent)
    
    logger.info(f"User logged in: {user.email}")
    
    return Response({
        'success': True,
        'message': 'Login successful',
        'user': UserResponseSerializer(user).data,
        'tokens': tokens,
        'password_change_required': user.last_password_change is None
    }, status=status.HTTP_200_OK)


# =============================================================================
# Logout
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """Logout user and invalidate tokens."""
    serializer = LogoutSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    refresh_token = data.get('refresh_token')
    
    try:
        if refresh_token:
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Invalidate session
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            UserSession.objects.filter(token_hash=token_hash).update(is_active=False)
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
        
    except TokenError:
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)


# =============================================================================
# Password Management
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def change_password(request):
    """Change user password."""
    serializer = PasswordChangeSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        user = User.objects.get(id=data['user_id'])
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not user.check_password(data['current_password']):
        return Response({
            'success': False,
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(data['new_password'])
    user.last_password_change = timezone.now()
    user.save(update_fields=['password', 'last_password_change'])
    
    logger.info(f"Password changed for user: {user.email}")
    
    return Response({
        'success': True,
        'message': 'Password changed successfully'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Request password reset email.
    
    Works for all user types: talents, partners, etc.
    The user_type parameter determines which portal's reset link is generated.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email'].lower()
    user_type = request.data.get('user_type', 'talent')  # talent, partner, api_service, data_layer
    portal_url = request.data.get('portal_url', '')  # Base URL for the reset link
    
    # Check if account exists
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        logger.info(f"Password reset requested for non-existent email: {email}")
        return Response({
            'success': False,
            'error': 'No account found with this email address. Please check the email or register for a new account.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Account exists - get client info
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Create reset token
    token = PasswordResetToken.create_for_user(
        user,
        ip_address=ip_address if ip_address else None,
        user_agent=user_agent
    )
    
    # Build reset URL based on user type
    if not portal_url:
        # Default portal URLs
        portal_urls = {
            'talent': 'http://localhost:9003',
            'partner': 'http://localhost:9004',
            'api_service': 'http://localhost:9001',
            'data_layer': 'http://localhost:9005',
        }
        portal_url = portal_urls.get(user_type, 'http://localhost:9003')
    
    reset_url = f"{portal_url.rstrip('/')}/reset-password/{token.token}/"
    
    # Send password reset email via communications service
    email_sent = False
    try:
        from communications.services import send_password_reset_email
        email_result = send_password_reset_email(
            full_name=user.get_full_name() or user.email,
            email=user.email,
            reset_url=reset_url
        )
        email_sent = email_result.get('success', False)
        
        if email_sent:
            logger.info(f"Password reset email sent to: {email}")
        else:
            logger.warning(f"Failed to send password reset email to {email}: {email_result.get('error')}")
    except Exception as e:
        logger.error(f"Exception sending password reset email to {email}: {e}")
    
    if not email_sent:
        return Response({
            'success': False,
            'error': 'Failed to send password reset email. Please try again later.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': True,
        'message': 'Password reset link has been sent to your email address.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset with token.
    
    Token is immediately invalidated after use.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        token_obj = PasswordResetToken.objects.get(token=data['token'])
    except PasswordResetToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid or expired reset link'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not token_obj.is_valid():
        if token_obj.used_at:
            error_msg = 'This reset link has already been used'
        else:
            error_msg = 'This reset link has expired'
        return Response({
            'success': False,
            'error': error_msg
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = token_obj.user
    user.set_password(data['new_password'])
    user.last_password_change = timezone.now()
    user.reset_failed_login()
    user.save(update_fields=['password', 'last_password_change', 'failed_login_attempts', 'locked_until'])
    
    # Mark token as used immediately (one-time use)
    token_obj.used_at = timezone.now()
    token_obj.save(update_fields=['used_at'])
    
    # Send password changed confirmation email
    try:
        from communications.services import send_password_changed_email
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        send_password_changed_email(
            to_email=user.email,
            full_name=user.get_full_name() or user.email,
            service_type=request.data.get('user_type', 'talent'),
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to send password changed email: {e}")
    
    logger.info(f"Password reset completed for: {user.email}")
    
    return Response({
        'success': True,
        'message': 'Password has been reset successfully. You can now log in with your new password.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_verify_token(request):
    """
    Verify if a password reset token is valid.
    
    Used by frontend to check if token is valid before showing reset form.
    """
    token = request.data.get('token', '')
    
    if not token:
        return Response({
            'success': False,
            'valid': False,
            'error': 'Token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token_obj = PasswordResetToken.objects.get(token=token)
        
        if not token_obj.is_valid():
            if token_obj.used_at:
                error_msg = 'This reset link has already been used'
            else:
                error_msg = 'This reset link has expired'
            return Response({
                'success': True,
                'valid': False,
                'error': error_msg
            })
        
        return Response({
            'success': True,
            'valid': True,
            'email': token_obj.user.email,
            'expires_at': token_obj.expires_at.isoformat()
        })
        
    except PasswordResetToken.DoesNotExist:
        return Response({
            'success': True,
            'valid': False,
            'error': 'Invalid reset link'
        })


# =============================================================================
# Token Management
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """Refresh access token using refresh token."""
    serializer = TokenRefreshSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    refresh_token = serializer.validated_data.get('refresh')
    
    try:
        token = RefreshToken(refresh_token)
        
        return Response({
            'success': True,
            'access': str(token.access_token),
            'access_expires': int(token.access_token.lifetime.total_seconds()),
        }, status=status.HTTP_200_OK)
        
    except TokenError as e:
        return Response({
            'success': False,
            'error': 'Invalid or expired refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_verify(request):
    """Verify if a token is valid."""
    serializer = TokenVerifySerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    token = serializer.validated_data.get('token')
    
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        AccessToken(token)
        
        return Response({
            'success': True,
            'valid': True
        }, status=status.HTTP_200_OK)
        
    except TokenError:
        return Response({
            'success': True,
            'valid': False
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_blacklist(request):
    """Blacklist/revoke a refresh token."""
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response({
            'success': False,
            'error': 'Refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        # Invalidate session
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        UserSession.objects.filter(token_hash=token_hash).update(is_active=False)
        
        return Response({
            'success': True,
            'message': 'Token blacklisted successfully'
        }, status=status.HTTP_200_OK)
        
    except TokenError:
        return Response({
            'success': False,
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Email Verification
# =============================================================================

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify user email with token."""
    token = request.data.get('token') or request.query_params.get('token')
    
    if not token:
        return Response({
            'success': False,
            'error': 'Verification token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerificationToken.objects.get(token=token)
        
        if not verification.is_valid():
            return Response({
                'success': False,
                'error': 'Verification link has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = verification.user
        user.is_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['is_verified', 'email_verified_at'])
        
        # Mark token as used
        verification.used_at = timezone.now()
        verification.save(update_fields=['used_at'])
        
        logger.info(f"Email verified for user: {user.email}")
        
        return Response({
            'success': True,
            'message': 'Email verified successfully. You can now log in.'
        }, status=status.HTTP_200_OK)
        
    except EmailVerificationToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid verification link'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    """Resend email verification link."""
    serializer = ResendVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email'].lower()
    
    try:
        user = User.objects.get(email__iexact=email)
        
        if user.is_verified:
            return Response({
                'success': True,
                'message': 'Email is already verified. You can log in.'
            }, status=status.HTTP_200_OK)
        
        # Create new verification token
        verification_token = EmailVerificationToken.create_for_user(user)
        
        # Send verification email
        try:
            from communications.services import send_registration_verification_email
            
            base_url = getattr(settings, 'TALENT_PORTAL_URL', 'https://talent.forgeforthafrica.com')
            verification_url = f"{base_url}/verify-email?token={verification_token.token}"
            
            send_registration_verification_email(
                full_name=user.full_name,
                email=user.email,
                verification_url=verification_url,
                token=verification_token.token
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
        
        return Response({
            'success': True,
            'message': 'Verification email sent. Please check your inbox.'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        # Don't reveal if email exists
        return Response({
            'success': True,
            'message': 'If an account exists with this email, a verification link will be sent.'
        }, status=status.HTTP_200_OK)


# =============================================================================
# Two-Factor Authentication
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def enable_2fa(request):
    """Enable two-factor authentication for user."""
    user_id = request.data.get('user_id')
    method = request.data.get('method', 'totp')
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        if user.two_factor_enabled:
            return Response({
                'success': False,
                'error': '2FA is already enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate TOTP secret
        import pyotp
        secret = pyotp.random_base32()
        
        user.two_factor_secret = secret
        user.two_factor_method = method
        user.save(update_fields=['two_factor_secret', 'two_factor_method'])
        
        # Generate provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='ForgeForth Africa'
        )
        
        return Response({
            'success': True,
            'secret': secret,
            'provisioning_uri': provisioning_uri,
            'message': 'Scan the QR code with your authenticator app, then verify to enable 2FA.'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except ImportError:
        return Response({
            'success': False,
            'error': '2FA module not available'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def disable_2fa(request):
    """Disable two-factor authentication for user."""
    user_id = request.data.get('user_id')
    code = request.data.get('code')
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        if not user.two_factor_enabled:
            return Response({
                'success': False,
                'error': '2FA is not enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify code before disabling
        if code:
            import pyotp
            totp = pyotp.TOTP(user.two_factor_secret)
            if not totp.verify(code):
                return Response({
                    'success': False,
                    'error': 'Invalid verification code'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_method = None
        user.save(update_fields=['two_factor_enabled', 'two_factor_secret', 'two_factor_method'])
        
        logger.info(f"2FA disabled for user: {user.email}")
        
        return Response({
            'success': True,
            'message': '2FA has been disabled'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa(request):
    """Verify 2FA code during login."""
    user_id = request.data.get('user_id')
    code = request.data.get('code')
    ip_address = request.data.get('ip_address')
    user_agent = request.data.get('user_agent')
    
    if not user_id or not code:
        return Response({
            'success': False,
            'error': 'User ID and code are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        if not user.two_factor_enabled:
            return Response({
                'success': False,
                'error': '2FA is not enabled for this user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify TOTP code
        import pyotp
        totp = pyotp.TOTP(user.two_factor_secret)
        
        if not totp.verify(code):
            # Check backup codes
            if user.two_factor_backup_codes:
                if code in user.two_factor_backup_codes:
                    # Remove used backup code
                    user.two_factor_backup_codes.remove(code)
                    user.save(update_fields=['two_factor_backup_codes'])
                else:
                    return Response({
                        'success': False,
                        'error': 'Invalid verification code'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid verification code'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Complete login
        user.reset_failed_login()
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        # Create session
        create_user_session(user, tokens['refresh'], ip_address=ip_address, user_agent=user_agent)
        
        # Record successful login
        record_login_attempt(user.email, 'success', user=user, ip_address=ip_address, user_agent=user_agent)
        
        logger.info(f"2FA verified for user: {user.email}")
        
        return Response({
            'success': True,
            'message': 'Verification successful',
            'user': UserResponseSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_backup_codes(request):
    """Get 2FA backup codes."""
    user_id = request.query_params.get('user_id')
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        if not user.two_factor_enabled:
            return Response({
                'success': False,
                'error': '2FA is not enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'backup_codes': user.two_factor_backup_codes or [],
            'codes_remaining': len(user.two_factor_backup_codes) if user.two_factor_backup_codes else 0
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def regenerate_backup_codes(request):
    """Regenerate 2FA backup codes."""
    user_id = request.data.get('user_id')
    code = request.data.get('code')  # Require 2FA verification
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        
        if not user.two_factor_enabled:
            return Response({
                'success': False,
                'error': '2FA is not enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify code if provided
        if code:
            import pyotp
            totp = pyotp.TOTP(user.two_factor_secret)
            if not totp.verify(code):
                return Response({
                    'success': False,
                    'error': 'Invalid verification code'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate new backup codes
        import secrets
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        user.two_factor_backup_codes = backup_codes
        user.save(update_fields=['two_factor_backup_codes'])
        
        logger.info(f"Backup codes regenerated for user: {user.email}")
        
        return Response({
            'success': True,
            'backup_codes': backup_codes,
            'message': 'New backup codes generated. Store them securely.'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# Session Management
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_sessions(request):
    """Get user's active sessions."""
    user_id = request.query_params.get('user_id')
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        sessions = UserSession.objects.filter(
            user_id=user_id,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity')
        
        sessions_data = [{
            'id': str(s.id),
            'device_name': s.device_name,
            'device_type': s.device_type,
            'ip_address': s.ip_address,
            'last_activity': s.last_activity.isoformat() if s.last_activity else None,
            'created_at': s.created_at.isoformat(),
            'is_current': False  # Would need to match against current token
        } for s in sessions]
        
        return Response({
            'success': True,
            'sessions': sessions_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch sessions'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def revoke_session(request, session_id):
    """Revoke a specific session."""
    user_id = request.data.get('user_id')
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = UserSession.objects.get(id=session_id, user_id=user_id)
        session.is_active = False
        session.save(update_fields=['is_active'])
        
        return Response({
            'success': True,
            'message': 'Session revoked successfully'
        }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def revoke_all_sessions(request):
    """Revoke all sessions except current."""
    user_id = request.data.get('user_id')
    current_token = request.data.get('current_token')  # Optional: to keep current session
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        sessions = UserSession.objects.filter(user_id=user_id, is_active=True)
        
        if current_token:
            current_hash = hashlib.sha256(current_token.encode()).hexdigest()
            sessions = sessions.exclude(token_hash=current_hash)
        
        count = sessions.update(is_active=False)
        
        return Response({
            'success': True,
            'message': f'{count} session(s) revoked',
            'revoked_count': count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error revoking sessions: {e}")
        return Response({
            'success': False,
            'error': 'Failed to revoke sessions'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Login History
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def login_history(request):
    """Get user's login history."""
    user_id = request.query_params.get('user_id')
    limit = int(request.query_params.get('limit', 20))
    
    if not user_id:
        return Response({
            'success': False,
            'error': 'User ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        history = LoginHistory.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
        
        history_data = [{
            'id': str(h.id),
            'status': h.status,
            'ip_address': h.ip_address,
            'user_agent': h.user_agent,
            'failure_reason': h.failure_reason,
            'created_at': h.created_at.isoformat()
        } for h in history]
        
        return Response({
            'success': True,
            'history': history_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching login history: {e}")
        return Response({
            'success': False,
            'error': 'Failed to fetch login history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

