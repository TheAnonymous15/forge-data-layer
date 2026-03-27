# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Partner Authentication Views
================================================
Separate authentication endpoints for partners/employers.
Partners use their own user table (partner_users).
"""
import logging
import hashlib
from datetime import timedelta

from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Organization
from .partner_models import (
    PartnerUser, PartnerSession, PartnerLoginHistory,
    PartnerEmailVerificationToken, PartnerPasswordResetToken
)
from .partner_serializers import (
    PartnerRegisterSerializer, PartnerLoginSerializer,
    PartnerUserResponseSerializer, PartnerEmailVerificationSerializer,
    PartnerPasswordChangeSerializer, PartnerPasswordResetRequestSerializer,
    PartnerPasswordResetConfirmSerializer
)

logger = logging.getLogger('data_layer.partner_auth')


def generate_partner_tokens(partner_user):
    """Generate JWT-like tokens for partner user."""
    import secrets
    
    # Generate access and refresh tokens
    access_token = secrets.token_urlsafe(64)
    refresh_token = secrets.token_urlsafe(64)
    
    return {
        'access': access_token,
        'refresh': refresh_token,
        'access_expires': 1800,  # 30 minutes
        'refresh_expires': 604800,  # 7 days
    }


def create_partner_session(partner_user, refresh_token, ip_address=None, user_agent=None):
    """Create a session record for partner user."""
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Parse device info
    device_type = 'desktop'
    device_name = 'Unknown'
    if user_agent:
        ua_lower = user_agent.lower()
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            device_type = 'mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device_type = 'tablet'
        
        if 'chrome' in ua_lower:
            device_name = 'Chrome Browser'
        elif 'firefox' in ua_lower:
            device_name = 'Firefox Browser'
        elif 'safari' in ua_lower:
            device_name = 'Safari Browser'
    
    return PartnerSession.objects.create(
        user=partner_user,
        token_hash=token_hash,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=timezone.now() + timedelta(days=7)
    )


def record_partner_login(email, status_val, user=None, ip_address=None, user_agent=None, failure_reason=None):
    """Record a partner login attempt."""
    PartnerLoginHistory.objects.create(
        user=user,
        email=email,
        status=status_val,
        ip_address=ip_address,
        user_agent=user_agent,
        failure_reason=failure_reason
    )


# =============================================================================
# Partner Registration
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def partner_register(request):
    """
    Register a new partner/organization.
    Creates both Organization and PartnerUser records.
    """
    serializer = PartnerRegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # Build phone number
        phone_number = None
        phone_code = data.get('phone_code', '').strip()
        phone = data.get('phone', '').strip()
        if phone_code and phone:
            phone_number = f"{phone_code}{phone}"
        elif phone:
            phone_number = phone
        
        # Generate unique slug for organization
        base_slug = slugify(data['organization_name'])
        slug = base_slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create Organization first (without owner - will update after creating user)
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
            owner=None,  # Will update after creating partner user
        )
        
        # Create Partner User
        partner_user = PartnerUser.objects.create(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_code=phone_code or None,
            phone_number=phone_number or None,
            organization=organization,
            role=PartnerUser.Role.OWNER,  # First user is owner
            job_title=data.get('job_title') or None,
            is_primary_contact=True,
            consent_authorized=data.get('consent_authorized', False),
            consent_terms_accepted=data.get('consent_terms', False),
            consent_data_processing=data.get('consent_data', False),
            terms_accepted_at=timezone.now() if data.get('consent_terms') else None,
            registration_ip=data.get('ip_address') or None,
            # Permissions for owner
            can_post_opportunities=True,
            can_manage_applications=True,
            can_manage_team=True,
            can_manage_settings=True,
            can_view_analytics=True,
        )
        partner_user.set_password(data['password'])
        partner_user.save()
        
        # Update organization owner
        organization.owner_id = partner_user.id
        organization.save(update_fields=['owner_id'])
        
        logger.info(f"Partner registered: {partner_user.email} for org: {organization.name}")
        
        # Create email verification token
        verification_token = PartnerEmailVerificationToken.create_for_user(partner_user)
        
        # Generate tokens
        tokens = generate_partner_tokens(partner_user)
        
        # Create session
        create_partner_session(
            partner_user,
            tokens['refresh'],
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )
        
        # Send verification email
        verification_email_sent = False
        try:
            from communications.services import send_registration_verification_email
            
            base_url = getattr(settings, 'PARTNER_PORTAL_URL', 'https://partners.forgeforthafrica.com')
            verification_url = f"{base_url}/verify-email?token={verification_token.token}"
            
            email_result = send_registration_verification_email(
                full_name=partner_user.full_name,
                email=partner_user.email,
                verification_url=verification_url,
                token=verification_token.token
            )
            verification_email_sent = email_result.get('success', False)
            if verification_email_sent:
                logger.info(f"Partner verification email sent to {partner_user.email}")
        except Exception as email_exc:
            logger.error(f"Exception sending partner verification email: {email_exc}")
        
        return Response({
            'success': True,
            'message': 'Partner registration successful. Please check your email to verify your account.',
            'user': {
                'id': str(partner_user.id),
                'email': partner_user.email,
                'first_name': partner_user.first_name,
                'last_name': partner_user.last_name,
                'full_name': partner_user.full_name,
                'job_title': partner_user.job_title,
                'role': partner_user.role,
                'is_verified': partner_user.is_verified,
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
            'verification_token': verification_token.token,  # For dev/testing
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Partner registration failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Partner registration failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Partner Login
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def partner_login(request):
    """Authenticate partner user and return tokens."""
    serializer = PartnerLoginSerializer(data=request.data)
    
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
    
    try:
        partner_user = PartnerUser.objects.select_related('organization').get(email=email)
    except PartnerUser.DoesNotExist:
        record_partner_login(email, 'failed', ip_address=ip_address, user_agent=user_agent, failure_reason='User not found')
        return Response({
            'success': False,
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if account is locked
    if partner_user.is_locked():
        record_partner_login(email, 'locked', user=partner_user, ip_address=ip_address, user_agent=user_agent)
        return Response({
            'success': False,
            'error': 'Account is temporarily locked. Please try again later.',
            'code': 'ACCOUNT_LOCKED'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check password
    if not partner_user.check_password(password):
        partner_user.increment_failed_login()
        record_partner_login(email, 'failed', user=partner_user, ip_address=ip_address, user_agent=user_agent, failure_reason='Invalid password')
        return Response({
            'success': False,
            'error': 'Invalid email or password'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if account is active
    if not partner_user.is_active:
        record_partner_login(email, 'failed', user=partner_user, ip_address=ip_address, user_agent=user_agent, failure_reason='Account inactive')
        return Response({
            'success': False,
            'error': 'Account is deactivated. Please contact support.',
            'code': 'ACCOUNT_INACTIVE'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if email is verified
    if not partner_user.is_verified:
        record_partner_login(email, 'failed', user=partner_user, ip_address=ip_address, user_agent=user_agent, failure_reason='Email not verified')
        return Response({
            'success': False,
            'error': 'Please verify your email before logging in.',
            'code': 'EMAIL_NOT_VERIFIED',
            'email': email,
            'can_resend': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Success - reset failed attempts
    partner_user.reset_failed_login()
    record_partner_login(email, 'success', user=partner_user, ip_address=ip_address, user_agent=user_agent)
    
    # Generate tokens
    tokens = generate_partner_tokens(partner_user)
    
    # Create session
    create_partner_session(partner_user, tokens['refresh'], ip_address=ip_address, user_agent=user_agent)
    
    logger.info(f"Partner login successful: {email}")
    
    return Response({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': str(partner_user.id),
            'email': partner_user.email,
            'first_name': partner_user.first_name,
            'last_name': partner_user.last_name,
            'full_name': partner_user.full_name,
            'phone_code': partner_user.phone_code,
            'phone_number': partner_user.phone_number,
            'role': partner_user.role,
            'job_title': partner_user.job_title,
            'organization_id': str(partner_user.organization.id),
            'organization_name': partner_user.organization.name,
            'is_verified': partner_user.is_verified,
            'is_primary_contact': partner_user.is_primary_contact,
            'two_factor_enabled': partner_user.two_factor_enabled,
            'last_login': partner_user.last_login.isoformat() if partner_user.last_login else None,
        },
        'organization': {
            'id': str(partner_user.organization.id),
            'name': partner_user.organization.name,
            'slug': partner_user.organization.slug,
            'industry': partner_user.organization.industry,
            'verification_status': partner_user.organization.verification_status,
        },
        'tokens': tokens,
    })


# =============================================================================
# Partner Email Verification
# =============================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def partner_verify_email(request):
    """Verify partner email address."""
    token = request.data.get('token') or request.query_params.get('token')
    
    if not token:
        return Response({
            'success': False,
            'error': 'Verification token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification_token = PartnerEmailVerificationToken.objects.select_related('user').get(token=token)
    except PartnerEmailVerificationToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid verification token'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not verification_token.is_valid():
        if verification_token.is_used:
            return Response({
                'success': False,
                'error': 'This verification link has already been used'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'error': 'Verification link has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Mark token as used
    verification_token.mark_used()
    
    # Verify the user
    partner_user = verification_token.user
    partner_user.is_verified = True
    partner_user.save(update_fields=['is_verified'])
    
    logger.info(f"Partner email verified: {partner_user.email}")
    
    return Response({
        'success': True,
        'message': 'Email verified successfully. You can now log in.'
    })


# =============================================================================
# Partner Resend Verification
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def partner_resend_verification(request):
    """Resend verification email to partner."""
    email = request.data.get('email', '').lower().strip()
    
    if not email:
        return Response({
            'success': False,
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        partner_user = PartnerUser.objects.get(email=email)
    except PartnerUser.DoesNotExist:
        # Don't reveal if user exists
        return Response({
            'success': True,
            'message': 'If an account exists with this email, a verification link will be sent.'
        })
    
    if partner_user.is_verified:
        return Response({
            'success': False,
            'error': 'This email is already verified.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create new verification token
    verification_token = PartnerEmailVerificationToken.create_for_user(partner_user)
    
    # Send email
    verification_email_sent = False
    try:
        from communications.services import send_registration_verification_email
        
        base_url = getattr(settings, 'PARTNER_PORTAL_URL', 'https://partners.forgeforthafrica.com')
        verification_url = f"{base_url}/verify-email?token={verification_token.token}"
        
        email_result = send_registration_verification_email(
            full_name=partner_user.full_name,
            email=partner_user.email,
            verification_url=verification_url,
            token=verification_token.token
        )
        verification_email_sent = email_result.get('success', False)
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
    
    return Response({
        'success': True,
        'message': 'If an account exists with this email, a verification link will be sent.',
        'verification_token': verification_token.token if settings.DEBUG else None,
    })


# =============================================================================
# Partner Logout
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def partner_logout(request):
    """Logout partner user (invalidate session)."""
    # In a real implementation, you'd invalidate the token/session
    return Response({
        'success': True,
        'message': 'Logged out successfully'
    })


# =============================================================================
# Partner Password Reset
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def partner_password_reset_request(request):
    """Request password reset for partner."""
    email = request.data.get('email', '').lower().strip()
    
    if not email:
        return Response({
            'success': False,
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Basic email format validation
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return Response({
            'success': False,
            'error': 'Please enter a valid email address'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if account exists
    try:
        partner_user = PartnerUser.objects.get(email=email)
    except PartnerUser.DoesNotExist:
        logger.info(f"Password reset requested for non-existent partner email: {email}")
        return Response({
            'success': False,
            'error': 'No account found with this email address. Please check the email or register for a new account.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Account exists - create reset token
    reset_token = PartnerPasswordResetToken.create_for_user(partner_user)
    
    # Build reset URL
    base_url = getattr(settings, 'PARTNER_PORTAL_URL', 'http://localhost:9004')
    reset_url = f"{base_url}/reset-password/{reset_token.token}/"
    
    # Send email
    email_sent = False
    try:
        from communications.services import send_password_reset_email
        email_result = send_password_reset_email(
            full_name=partner_user.full_name or partner_user.email,
            email=partner_user.email,
            reset_url=reset_url
        )
        email_sent = email_result.get('success', False)
        
        if email_sent:
            logger.info(f"Password reset email sent to partner: {email}")
        else:
            logger.warning(f"Failed to send password reset email to partner {email}: {email_result.get('error')}")
    except Exception as e:
        logger.error(f"Exception sending password reset email to partner {email}: {e}")
    
    if not email_sent:
        return Response({
            'success': False,
            'error': 'Failed to send password reset email. Please try again later.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': True,
        'message': 'Password reset link has been sent to your email address.'
    })
    
    return Response({
        'success': True,
        'message': 'If an account exists with this email, a password reset link will be sent.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def partner_password_reset_verify_token(request):
    """Verify if a partner password reset token is valid."""
    token = request.data.get('token', '')
    
    if not token:
        return Response({
            'success': False,
            'valid': False,
            'error': 'Token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        reset_token = PartnerPasswordResetToken.objects.select_related('user').get(token=token)
        
        if not reset_token.is_valid():
            if reset_token.used_at:
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
            'email': reset_token.user.email,
            'expires_at': reset_token.expires_at.isoformat() if reset_token.expires_at else None
        })
        
    except PartnerPasswordResetToken.DoesNotExist:
        return Response({
            'success': True,
            'valid': False,
            'error': 'Invalid reset link'
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def partner_password_reset_confirm(request):
    """Confirm password reset for partner."""
    serializer = PartnerPasswordResetConfirmSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'Validation failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    token = data['token']
    new_password = data['new_password']
    
    try:
        reset_token = PartnerPasswordResetToken.objects.select_related('user').get(token=token)
    except PartnerPasswordResetToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid reset token'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not reset_token.is_valid():
        return Response({
            'success': False,
            'error': 'Reset link has expired. Please request a new one.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update password
    partner_user = reset_token.user
    partner_user.set_password(new_password)
    partner_user.last_password_change = timezone.now()
    partner_user.save(update_fields=['password', 'last_password_change'])
    
    # Mark token as used
    reset_token.mark_used()
    
    logger.info(f"Partner password reset successful: {partner_user.email}")
    
    return Response({
        'success': True,
        'message': 'Password reset successful. You can now log in with your new password.'
    })

