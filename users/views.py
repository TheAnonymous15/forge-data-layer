# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer User Views
=========================================
API endpoints for user management.
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, LoginSerializer, VerifyEmailSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, PasswordChangeSerializer
)
from .models import LoginHistory
from tokens.models import EmailVerificationToken, PasswordResetToken

logger = logging.getLogger('data_layer')
User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.

    Provides CRUD operations and authentication endpoints.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'login', 'verify_email', 'forgot_password', 'reset_password', 'check_email', 'check_phone']:
            return [permissions.AllowAny()]
        return super().get_permissions()

    @extend_schema(
        summary="Register a new user",
        tags=['users']
    )
    def create(self, request, *args, **kwargs):
        """Register a new user account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if email exists
        if User.objects.filter(email__iexact=serializer.validated_data['email']).exists():
            return Response(
                {'error': 'An account with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if phone exists (if provided)
        phone = serializer.validated_data.get('phone_number')
        if phone and User.objects.filter(phone_number=phone).exists():
            return Response(
                {'error': 'An account with this phone number already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user
        user = serializer.save(
            registration_ip=self.get_client_ip(request)
        )

        # Create verification token
        token = EmailVerificationToken.create_for_user(user)

        logger.info(f"New user registered: {user.email} (role: {user.role})")

        return Response({
            'success': True,
            'message': 'Registration successful. Please verify your email.',
            'user': UserSerializer(user).data,
            'verification_token': token.token  # Return token for email service to use
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Login user",
        request=LoginSerializer,
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Authenticate user and return tokens."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        remember_me = serializer.validated_data.get('remember_me', False)
        device_info = serializer.validated_data.get('device_info', {})

        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get user
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            self.log_login(None, email, 'failed', ip_address, user_agent, device_info, 'User not found')
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if locked
        if user.is_locked():
            self.log_login(user, email, 'blocked', ip_address, user_agent, device_info, 'Account locked')
            return Response(
                {'error': 'Account is temporarily locked. Please try again later.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check password
        if not user.check_password(password):
            user.increment_failed_login()
            self.log_login(user, email, 'failed', ip_address, user_agent, device_info, 'Invalid password')
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if active
        if not user.is_active:
            self.log_login(user, email, 'blocked', ip_address, user_agent, device_info, 'Account deactivated')
            return Response(
                {'error': 'Your account has been deactivated. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if verified
        if not user.is_verified:
            return Response({
                'success': False,
                'requires_verification': True,
                'message': 'Please verify your email before logging in.'
            }, status=status.HTTP_200_OK)

        # Check 2FA
        if user.two_factor_enabled:
            from tokens.models import TwoFactorSession
            session = TwoFactorSession.create_for_user(user, ip_address)
            self.log_login(user, email, 'requires_2fa', ip_address, user_agent, device_info)
            return Response({
                'success': False,
                'requires_2fa': True,
                'session_token': session.token,
                'message': 'Two-factor authentication required'
            }, status=status.HTTP_200_OK)

        # Reset failed attempts and update last login
        user.reset_failed_login()
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Log successful login
        self.log_login(user, email, 'success', ip_address, user_agent, device_info)

        logger.info(f"User logged in: {user.email}")

        return Response({
            'success': True,
            'message': 'Login successful',
            'user': UserDetailSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Verify email address",
        request=VerifyEmailSerializer,
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        """Verify user email with token."""
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['token']

        try:
            token = EmailVerificationToken.objects.get(token=token_str)
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not token.is_valid():
            return Response(
                {'error': 'Token has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark user as verified
        user = token.user
        user.is_verified = True
        user.save(update_fields=['is_verified'])

        # Mark token as used
        token.mark_used()

        logger.info(f"Email verified: {user.email}")

        return Response({
            'success': True,
            'message': 'Email verified successfully. You can now log in.'
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Request password reset",
        request=ForgotPasswordSerializer,
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        """Request password reset email."""
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].lower()

        # Always return success to prevent email enumeration
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            token = PasswordResetToken.create_for_user(
                user,
                ip_address=self.get_client_ip(request)
            )

            # Return token for email service
            return Response({
                'success': True,
                'message': 'If an account exists with this email, a password reset link has been sent.',
                'reset_token': token.token,  # For email service
                'user_id': str(user.id),
                'user_email': user.email,
                'user_first_name': user.first_name
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            pass

        return Response({
            'success': True,
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Reset password",
        request=ResetPasswordSerializer,
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Reset password using token."""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            token = PasswordResetToken.objects.get(token=token_str)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not token.is_valid():
            return Response(
                {'error': 'Token has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update password
        user = token.user
        user.set_password(new_password)
        user.last_password_change = timezone.now()
        user.save(update_fields=['password', 'last_password_change'])

        # Mark token as used
        token.mark_used()

        logger.info(f"Password reset: {user.email}")

        return Response({
            'success': True,
            'message': 'Password reset successful. You can now log in with your new password.'
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Change password",
        request=PasswordChangeSerializer,
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change password for authenticated user."""
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])
        user.last_password_change = timezone.now()
        user.save(update_fields=['password', 'last_password_change'])

        logger.info(f"Password changed: {user.email}")

        return Response({
            'success': True,
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Check if email exists",
        parameters=[OpenApiParameter('email', str, required=True)],
        tags=['users']
    )
    @action(detail=False, methods=['get', 'post'])
    def check_email(self, request):
        """Check if email is already registered."""
        email = request.query_params.get('email', '') or request.data.get('email', '')
        email = email.lower() if email else ''
        exists = User.objects.filter(email__iexact=email).exists()
        return Response({'exists': exists})
        return Response({'exists': exists})

    @extend_schema(
        summary="Check if phone exists",
        parameters=[OpenApiParameter('phone', str, required=True)],
        tags=['users']
    )
    @action(detail=False, methods=['get', 'post'])
    def check_phone(self, request):
        """Check if phone number is already registered."""
        phone = request.query_params.get('phone', '') or request.data.get('phone_number', '') or request.data.get('phone', '')
        exists = User.objects.filter(phone_number=phone).exists() if phone else False
        return Response({'exists': exists})

    @extend_schema(
        summary="Create verification token for user",
        tags=['users']
    )
    @action(detail=True, methods=['post'])
    def create_verification_token(self, request, pk=None):
        """Create a new verification token for user."""
        user = self.get_object()
        token = EmailVerificationToken.create_for_user(user)

        return Response({
            'success': True,
            'token': token.token,
            'user_id': str(user.id),
            'user_email': user.email,
            'user_first_name': user.first_name
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get current user",
        tags=['users']
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current authenticated user."""
        return Response(UserDetailSerializer(request.user).data)

    @extend_schema(
        summary="Resend verification email",
        tags=['users']
    )
    @action(detail=False, methods=['post'])
    def resend_verification(self, request):
        """Resend email verification."""
        email = request.data.get('email', '').lower()

        try:
            user = User.objects.get(email__iexact=email, is_verified=False)
            token = EmailVerificationToken.create_for_user(user)

            return Response({
                'success': True,
                'message': 'Verification email has been sent.',
                'verification_token': token.token,
                'user_email': user.email,
                'user_first_name': user.first_name
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            pass

        return Response({
            'success': True,
            'message': 'If an unverified account exists with this email, a verification link has been sent.'
        }, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def log_login(self, user, email, status, ip_address, user_agent, device_info=None, failure_reason=None):
        """Log login attempt."""
        LoginHistory.objects.create(
            user=user,
            email=email,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info or {},
            failure_reason=failure_reason
        )

