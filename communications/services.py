# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Communications Internal Services
====================================================
Internal service functions for sending emails, notifications, etc.
These are called internally by other Data Layer modules - NO HTTP overhead.
"""
import logging
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from .models import EmailLog, Notification

logger = logging.getLogger('data_layer.communications')


# =============================================================================
# Email Configuration
# =============================================================================

DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'ForgeForth Africa <mailer@forgeforthafrica.com>')
SUPPORT_EMAIL = getattr(settings, 'SUPPORT_EMAIL', 'support@forgeforthafrica.com')
CONTACT_EMAIL = getattr(settings, 'CONTACT_EMAIL', 'info@forgeforthafrica.com')


# =============================================================================
# Email Templates (HTML)
# =============================================================================

def get_base_email_template(content, title="ForgeForth Africa"):
    """Wrap content in base email template - matching the standard ForgeForth design."""
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #0a0f1a;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0f1a; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 520px; background: linear-gradient(135deg, #141c2e 0%, #0f172a 100%); border-radius: 16px; border: 1px solid rgba(45, 55, 72, 0.6); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                    <tr>
                        <td style="padding: 40px;">
                            <!-- Logo -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 24px; border-radius: 8px; border: 1px solid rgba(20, 184, 166, 0.3);">ForgeForth Africa</span>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Content -->
                            {content}
                            
                            <!-- Footer -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.1);">
                                <tr>
                                    <td align="center">
                                        <p style="color: #64748b; font-size: 12px; margin: 0;">&copy; {datetime.now().year} ForgeForth Africa</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''


# =============================================================================
# Internal Email Sending Functions
# =============================================================================

def send_email_internal(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: str = None,
    from_email: str = None,
    template_name: str = None,
    context: dict = None,
    recipient_id: str = None
) -> dict:
    """
    Send email internally - used by other Data Layer services.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        plain_content: Plain text email body (auto-generated if not provided)
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        template_name: Name of template for logging
        context: Context data for logging
        recipient_id: User ID if recipient is a registered user

    Returns:
        dict with 'success', 'email_log_id', and optionally 'error'
    """
    from_email = from_email or DEFAULT_FROM_EMAIL
    plain_content = plain_content or strip_tags(html_content)

    # Create email log entry first
    email_log = EmailLog.objects.create(
        recipient_id=recipient_id,
        recipient_email=to_email,
        subject=subject,
        template_name=template_name or 'custom',
        template_context=context or {},
        status='pending'
    )

    try:
        # Create email with both HTML and plain text
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")

        # Send the email
        email.send(fail_silently=False)

        # Update log on success
        email_log.status = 'sent'
        email_log.sent_at = timezone.now()
        email_log.save(update_fields=['status', 'sent_at'])

        logger.info(f"Email sent successfully to {to_email}: {subject}")

        return {
            'success': True,
            'email_log_id': str(email_log.id),
            'message': 'Email sent successfully'
        }

    except Exception as e:
        # Update log on failure
        email_log.status = 'failed'
        email_log.error_message = str(e)
        email_log.save(update_fields=['status', 'error_message'])

        logger.error(f"Failed to send email to {to_email}: {e}")

        return {
            'success': False,
            'email_log_id': str(email_log.id),
            'error': str(e)
        }


# =============================================================================
# Access Request Email Functions
# =============================================================================

def send_access_request_confirmation(full_name: str, email: str, service_type: str, request_id: str) -> dict:
    """
    Send confirmation email when access request is submitted.
    Called internally by the access request creation function.
    """
    service_name = "API Service Documentation" if service_type == "api_service" else "Data Layer Documentation"
    first_name = full_name.split()[0] if full_name else "there"

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">Access Request Received.</h1>
        
        <!-- Body -->
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
           Greetings {first_name}, thank you for your interest in ForgeForth Africa. We have received your access request for the <strong style="color: #fff;">{service_name}</strong>.
        </p>
        
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            Our team will review your request and get back to you within 24-48 hours.
        </p>
        
        <!-- Info Box -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; margin-bottom: 24px;">
            <tr>
                <td style="padding: 16px;">
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0 0 8px 0;"><strong>Request ID:</strong> {request_id[:8]}...</p>
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0 0 8px 0;"><strong>Service:</strong> {service_name}</p>
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0;"><strong>Status:</strong> <span style="color: #fbbf24;">Pending Review</span></p>
                </td>
            </tr>
        </table>
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td>
                    <a href="https://forgeforthafrica.com" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">Visit ForgeForth Africa</a>
                </td>
            </tr>
        </table>
        
        <!-- Security Notice -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(234, 179, 8, 0.1); border-left: 3px solid #eab308; border-radius: 0 6px 6px 0; margin-bottom: 16px;">
            <tr>
                <td style="padding: 12px 16px;">
                    <p style="color: #fbbf24; font-size: 13px; font-weight: 600; margin: 0 0 4px 0;">Didn't request this?</p>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0;">If you didn't make this request, please ignore this email or contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color: #8b5cf6; text-decoration: none;">{SUPPORT_EMAIL}</a></p>
                </td>
            </tr>
        </table>
    ''', title="Access Request Received")

    return send_email_internal(
        to_email=email,
        subject="ForgeForth Africa - Access Request Received",
        html_content=html_content,
        template_name='access_request_confirmation',
        context={
            'full_name': full_name,
            'service_type': service_type,
            'request_id': request_id
        }
    )


def send_access_request_approved(
    full_name: str,
    email: str,
    service_type: str,
    username: str,
    temp_password: str = None,
    login_url: str = None
) -> dict:
    """
    Send approval email when access request is approved.
    """
    service_name = "API Service" if service_type == "api_service" else "Data Layer"
    first_name = full_name.split()[0] if full_name else "there"
    login_url = login_url or f"https://{'api' if service_type == 'api_service' else 'data'}.forgeforthafrica.com/login"

    # Password section
    password_html = ""
    if temp_password:
        password_html = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; margin-bottom: 24px;">
            <tr>
                <td style="padding: 16px;">
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0 0 8px 0;"><strong>Username:</strong> <span style="color: #fff;">{username}</span></p>
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0 0 12px 0;"><strong>Temporary Password:</strong> <span style="color: #fff; font-family: monospace;">{temp_password}</span></p>
                    <p style="color: #fbbf24; font-size: 12px; margin: 0;">⚠️ Please change your password after first login.</p>
                </td>
            </tr>
        </table>
        '''
    else:
        password_html = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; margin-bottom: 24px;">
            <tr>
                <td style="padding: 16px;">
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0;"><strong>Username:</strong> <span style="color: #fff;">{username}</span></p>
                </td>
            </tr>
        </table>
        '''

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">Welcome to ForgeForth Africa, {first_name}!</h1>
        
        <!-- Body -->
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
            Great news! Your access request for the <strong style="color: #fff;">{service_name}</strong> has been approved.
        </p>
        
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            You can now access the documentation and start building with our platform.
        </p>
        
        <!-- Credentials Box -->
        {password_html}
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td>
                    <a href="{login_url}" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">Login Now</a>
                </td>
            </tr>
        </table>
        
        <!-- Security Notice -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(234, 179, 8, 0.1); border-left: 3px solid #eab308; border-radius: 0 6px 6px 0;">
            <tr>
                <td style="padding: 12px 16px;">
                    <p style="color: #fbbf24; font-size: 13px; font-weight: 600; margin: 0 0 4px 0;">Didn't request this?</p>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0;">If you didn't request access, please contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color: #8b5cf6; text-decoration: none;">{SUPPORT_EMAIL}</a></p>
                </td>
            </tr>
        </table>
    ''', title="Access Request Approved")

    return send_email_internal(
        to_email=email,
        subject="ForgeForth Africa - Access Request Approved! 🎉",
        html_content=html_content,
        template_name='access_request_approved',
        context={
            'full_name': full_name,
            'service_type': service_type,
            'username': username
        }
    )


def send_access_request_rejected(
    full_name: str,
    email: str,
    service_type: str,
    rejection_reason: str = None
) -> dict:
    """
    Send rejection email when access request is rejected.
    """
    service_name = "API Service" if service_type == "api_service" else "Data Layer"
    first_name = full_name.split()[0] if full_name else "there"
    reason = rejection_reason or "Your request did not meet our current requirements."

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">Access Request Update, {first_name}</h1>
        
        <!-- Body -->
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
            Thank you for your interest in the ForgeForth Africa <strong style="color: #fff;">{service_name}</strong>.
        </p>
        
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            After careful review, we are unable to approve your access request at this time.
        </p>
        
        <!-- Reason Box -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; margin-bottom: 24px;">
            <tr>
                <td style="padding: 16px;">
                    <p style="color: #fca5a5; font-size: 13px; font-weight: 600; margin: 0 0 8px 0;">Reason:</p>
                    <p style="color: #cbd5e1; font-size: 14px; margin: 0;">{reason}</p>
                </td>
            </tr>
        </table>
        
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            This decision is not final. You may submit a new request with additional information or contact our support team for clarification.
        </p>
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td>
                    <a href="mailto:{SUPPORT_EMAIL}" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">Contact Support</a>
                </td>
            </tr>
        </table>
    ''', title="Access Request Update")

    return send_email_internal(
        to_email=email,
        subject="ForgeForth Africa - Access Request Update",
        html_content=html_content,
        template_name='access_request_rejected',
        context={
            'full_name': full_name,
            'service_type': service_type,
            'rejection_reason': reason
        }
    )


# =============================================================================
# User Registration Email Functions
# =============================================================================

def send_registration_verification_email(
    full_name: str,
    email: str,
    verification_url: str,
    token: str
) -> dict:
    """Send email verification link after registration."""
    first_name = full_name.split()[0] if full_name else "there"

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0 0 20px 0;">Welcome to ForgeForth Africa, {first_name}!</h1>
        
        <!-- Body -->
        <p style="color: #a0aec0; font-size: 15px; line-height: 1.7; margin: 0 0 16px 0;">
            Thank you for creating an account with us. You're one step away from joining Africa's leading talent platform.
        </p>
        
        <p style="color: #a0aec0; font-size: 15px; line-height: 1.7; margin: 0 0 24px 0;">
            Please verify your email address to activate your account:
        </p>
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
            <tr>
                <td>
                    <a href="{verification_url}" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #ffffff; font-size: 15px; font-weight: 600; padding: 14px 32px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 14px 0 rgba(34, 197, 94, 0.4);">Verify My Email</a>
                </td>
            </tr>
        </table>
        
        <p style="color: #a0aec0; font-size: 14px; margin: 0 0 24px 0;">
            This link is valid for <strong style="color: #ffffff;">24 hours</strong>.
        </p>
        
        <!-- Security Notice -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(139, 92, 246, 0.08); border-left: 3px solid #8b5cf6; border-radius: 0 8px 8px 0;">
            <tr>
                <td style="padding: 14px 18px;">
                    <p style="color: #f87171; font-size: 14px; font-weight: 600; margin: 0 0 6px 0;">Didn't register?</p>
                    <p style="color: #a0aec0; font-size: 13px; line-height: 1.6; margin: 0;">If you didn't create this account, please ignore this email, delete it or contact us at <a href="mailto:security@forgeforthafrica.com" style="color: #60a5fa; text-decoration: none;">security@forgeforthafrica.com</a></p>
                </td>
            </tr>
        </table>
    ''', title="Verify Your Email - ForgeForth Africa")

    return send_email_internal(
        to_email=email,
        subject="Verify Your Email - ForgeForth Africa",
        html_content=html_content,
        template_name='registration_verification',
        context={
            'full_name': full_name,
            'verification_url': verification_url
        }
    )


def send_welcome_email(full_name: str, email: str, user_type: str = 'talent') -> dict:
    """Send welcome email after successful registration."""
    first_name = full_name.split()[0] if full_name else "there"
    portal_url = "https://talent.forgeforthafrica.com" if user_type == 'talent' else "https://partners.forgeforthafrica.com"

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">You're All Set, {first_name}! 🎉</h1>
        
        <!-- Body -->
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
            Your email has been verified and your account is now active. Welcome to the future of talent management in Africa!
        </p>
        
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            Here's what you can do next:
        </p>
        
        <!-- Features List -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td style="padding: 8px 0;">
                    <span style="color: #22c55e; margin-right: 8px;">✓</span>
                    <span style="color: #cbd5e1; font-size: 14px;">Complete your profile</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <span style="color: #22c55e; margin-right: 8px;">✓</span>
                    <span style="color: #cbd5e1; font-size: 14px;">Explore opportunities</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <span style="color: #22c55e; margin-right: 8px;">✓</span>
                    <span style="color: #cbd5e1; font-size: 14px;">Connect with partners</span>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 0;">
                    <span style="color: #22c55e; margin-right: 8px;">✓</span>
                    <span style="color: #cbd5e1; font-size: 14px;">Showcase your skills</span>
                </td>
            </tr>
        </table>
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td>
                    <a href="{portal_url}/dashboard" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">Go to Dashboard</a>
                </td>
            </tr>
        </table>
        
        <p style="color: #64748b; font-size: 13px; margin: 0;">
            Need help? Our support team is always here for you at <a href="mailto:{SUPPORT_EMAIL}" style="color: #8b5cf6; text-decoration: none;">{SUPPORT_EMAIL}</a>
        </p>
    ''', title="Welcome to ForgeForth Africa")

    return send_email_internal(
        to_email=email,
        subject="Welcome to ForgeForth Africa! 🎉",
        html_content=html_content,
        template_name='welcome',
        context={
            'full_name': full_name,
            'user_type': user_type
        }
    )


# =============================================================================
# Internal Notification Functions
# =============================================================================

def create_notification_internal(
    recipient_id: str,
    title: str,
    body: str,
    notif_type: str = 'system',
    channel: str = 'in_app',
    action_url: str = '',
    data: dict = None
) -> dict:
    """
    Create notification internally - used by other Data Layer services.

    Returns:
        dict with 'success', 'notification_id', and optionally 'error'
    """
    try:
        notification = Notification.objects.create(
            recipient_id=recipient_id,
            notif_type=notif_type,
            channel=channel,
            title=title,
            body=body,
            action_url=action_url,
            data=data or {},
            status='sent',
            sent_at=timezone.now()
        )

        logger.info(f"Notification created for user {recipient_id}: {title}")

        return {
            'success': True,
            'notification_id': str(notification.id)
        }

    except Exception as e:
        logger.error(f"Failed to create notification for user {recipient_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# =============================================================================
# Password Reset Email
# =============================================================================

def send_password_reset_email(
    full_name: str,
    email: str,
    reset_url: str
) -> dict:
    """Send password reset link."""
    first_name = full_name.split()[0] if full_name else "there"

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">Reset Your Password, {first_name}</h1>
        
        <!-- Body -->
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">
            We received a request to reset your password. Click the button below to create a new password:
        </p>
        
        <!-- Button -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
            <tr>
                <td>
                    <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">Reset Password</a>
                </td>
            </tr>
        </table>
        
        <p style="color: #94a3b8; font-size: 14px; margin: 0 0 24px 0;">
            This link is valid for <strong style="color: #fff;">1 hour</strong>.
        </p>
        
        <!-- Security Notice -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(234, 179, 8, 0.1); border-left: 3px solid #eab308; border-radius: 0 6px 6px 0;">
            <tr>
                <td style="padding: 12px 16px;">
                    <p style="color: #fbbf24; font-size: 13px; font-weight: 600; margin: 0 0 4px 0;">Didn't request this?</p>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0;">If you didn't request a password reset, please ignore this email or contact us at <a href="mailto:security@forgeforthafrica.com" style="color: #8b5cf6; text-decoration: none;">security@forgeforthafrica.com</a></p>
                </td>
            </tr>
        </table>
    ''', title="Reset Your Password")

    return send_email_internal(
        to_email=email,
        subject="ForgeForth Africa - Reset Your Password",
        html_content=html_content,
        template_name='password_reset',
        context={
            'full_name': full_name,
            'reset_url': reset_url
        }
    )


# =============================================================================
# Generic Email Function
# =============================================================================

def send_generic_email(
    to_email: str,
    subject: str,
    title: str,
    body_paragraphs: list,
    button_text: str = None,
    button_url: str = None,
    info_box_content: str = None
) -> dict:
    """
    Send a generic formatted email.

    Args:
        to_email: Recipient email
        subject: Email subject
        title: Email title (H1)
        body_paragraphs: List of paragraph strings
        button_text: Optional CTA button text
        button_url: Optional CTA button URL
        info_box_content: Optional info box HTML content
    """
    paragraphs_html = ''.join([
        f'<p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;">{p}</p>'
        for p in body_paragraphs
    ])

    button_html = ""
    if button_text and button_url:
        button_html = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
            <tr>
                <td>
                    <a href="{button_url}" style="display: inline-block; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 12px 28px; border-radius: 6px; text-decoration: none;">{button_text}</a>
                </td>
            </tr>
        </table>
        '''

    info_box_html = ""
    if info_box_content:
        info_box_html = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; margin: 24px 0;">
            <tr>
                <td style="padding: 16px;">
                    {info_box_content}
                </td>
            </tr>
        </table>
        '''

    html_content = get_base_email_template(f'''
        <!-- Title -->
        <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">{title}</h1>
        
        {paragraphs_html}
        {info_box_html}
        {button_html}
    ''', title=title)

    return send_email_internal(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        template_name='generic'
    )


# =============================================================================
# Password Changed Email
# =============================================================================

def send_password_changed_email(
    to_email: str,
    full_name: str = None,
    service_type: str = 'platform',
    ip_address: str = None,
    user_agent: str = None
) -> dict:
    """
    Send password changed notification email.

    Args:
        to_email: Recipient email
        full_name: User's full name
        service_type: Type of service (api_service, data_layer, talent_portal, etc.)
        ip_address: IP address where password was changed
        user_agent: Browser/device information

    Returns:
        dict with success status
    """
    try:
        name = full_name or to_email.split('@')[0].replace('.', ' ').title()
        changed_at = timezone.now().strftime('%B %d, %Y at %I:%M %p UTC')

        service_names = {
            'api_service': 'API Service',
            'data_layer': 'Data Layer',
            'talent_portal': 'Talent Portal',
            'admin_portal': 'Admin Portal',
            'partner_portal': 'Partner Portal',
            'platform': 'ForgeForth Africa Platform'
        }
        service_display = service_names.get(service_type, 'ForgeForth Africa Platform')

        # Build security info
        security_info = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 8px; padding: 16px; margin: 20px 0;">
            <tr>
                <td>
                    <p style="color: #eab308; font-size: 13px; font-weight: 600; margin: 0 0 8px 0;">⚠️ Security Notice</p>
                    <p style="color: #94a3b8; font-size: 13px; margin: 0 0 4px 0;"><strong>Time:</strong> {changed_at}</p>
                    {f'<p style="color: #94a3b8; font-size: 13px; margin: 0 0 4px 0;"><strong>IP Address:</strong> {ip_address}</p>' if ip_address else ''}
                    {f'<p style="color: #94a3b8; font-size: 13px; margin: 0;"><strong>Device:</strong> {user_agent[:50]}...</p>' if user_agent else ''}
                </td>
            </tr>
        </table>
        '''

        html_content = get_base_email_template(f'''
            <h1 style="color: #fff; font-size: 22px; font-weight: 600; margin: 0 0 20px 0;">Password Changed Successfully</h1>
            
            <p style="color: #e2e8f0; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
                Hi {name},
            </p>
            
            <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
                Your password for <strong style="color: #a78bfa;">{service_display}</strong> has been successfully changed.
            </p>
            
            {security_info}
            
            <table width="100%" cellpadding="0" cellspacing="0" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 16px; margin: 20px 0;">
                <tr>
                    <td>
                        <p style="color: #ef4444; font-size: 13px; font-weight: 600; margin: 0 0 8px 0;">🚨 Wasn't You?</p>
                        <p style="color: #94a3b8; font-size: 13px; margin: 0;">
                            If you did not make this change, your account may be compromised. 
                            Please contact our security team <strong>immediately</strong> at 
                            <a href="mailto:security@forgeforthafrica.com" style="color: #ef4444; text-decoration: none;">security@forgeforthafrica.com</a>
                        </p>
                    </td>
                </tr>
            </table>
            
            <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 20px 0 0 0;">
                For your security, we recommend using a strong, unique password and enabling two-factor authentication when available.
            </p>
        ''', title="Password Changed - ForgeForth Africa")

        result = send_email_internal(
            to_email=to_email,
            subject="🔐 Password Changed - ForgeForth Africa",
            html_content=html_content,
            template_name='password_changed'
        )

        logger.info(f"Password changed email sent to {to_email} for {service_type}")
        return result

    except Exception as e:
        logger.error(f"Failed to send password changed email to {to_email}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

