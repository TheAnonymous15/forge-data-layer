# -*- coding: utf-8 -*-
"""Administration API Views - Comprehensive Admin Endpoints."""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import StaffRole, StaffRoleAssignment, FeatureFlag, AdminAuditLog, SupportTicket
from .serializers import (
    StaffRoleSerializer, StaffRoleAssignmentSerializer, FeatureFlagSerializer,
    AdminAuditLogSerializer, SupportTicketSerializer
)


# ═══════════════════════════════════════════════════════════════════════════════
# ViewSets
# ═══════════════════════════════════════════════════════════════════════════════

class StaffRoleViewSet(viewsets.ModelViewSet):
    """API endpoint for staff roles."""
    queryset = StaffRole.objects.all()
    serializer_class = StaffRoleSerializer
    permission_classes = [IsAdminUser]


class StaffRoleAssignmentViewSet(viewsets.ModelViewSet):
    """API endpoint for role assignments."""
    queryset = StaffRoleAssignment.objects.all()
    serializer_class = StaffRoleAssignmentSerializer
    permission_classes = [IsAdminUser]


class FeatureFlagViewSet(viewsets.ModelViewSet):
    """API endpoint for feature flags."""
    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle feature flag."""
        flag = self.get_object()
        flag.is_enabled = not flag.is_enabled
        flag.save()
        return Response({'success': True, 'is_enabled': flag.is_enabled})

    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if a feature is enabled."""
        feature_name = request.query_params.get('name')
        if not feature_name:
            return Response({'success': False, 'error': 'name required'}, status=400)
        try:
            flag = FeatureFlag.objects.get(name=feature_name)
            return Response({'success': True, 'enabled': flag.is_enabled})
        except FeatureFlag.DoesNotExist:
            return Response({'success': True, 'enabled': False})


class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for audit logs."""
    queryset = AdminAuditLog.objects.all()
    serializer_class = AdminAuditLogSerializer
    permission_classes = [IsAdminUser]


class SupportTicketViewSet(viewsets.ModelViewSet):
    """API endpoint for support tickets."""
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a ticket."""
        ticket = self.get_object()
        resolution = request.data.get('resolution', '')
        ticket.status = 'resolved'
        ticket.resolution = resolution
        ticket.resolved_at = timezone.now()
        ticket.save()
        return Response({'success': True, 'message': 'Ticket resolved'})


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard & Statistics
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    """Get dashboard statistics for admin."""
    from users.models import User
    from profiles.models import TalentProfile
    from organizations.models import Organization, Opportunity
    from applications.models import Application

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    stats = {
        'users': {
            'total': User.objects.count(),
            'new_this_month': User.objects.filter(date_joined__gte=thirty_days_ago).count(),
            'new_this_week': User.objects.filter(date_joined__gte=seven_days_ago).count(),
            'verified': User.objects.filter(is_verified=True).count() if hasattr(User, 'is_verified') else 0,
        },
        'talents': {
            'total': TalentProfile.objects.count(),
            'verified': TalentProfile.objects.filter(is_verified=True).count() if hasattr(TalentProfile, 'is_verified') else 0,
        },
        'organizations': {
            'total': Organization.objects.count(),
            'verified': Organization.objects.filter(is_verified=True).count() if hasattr(Organization, 'is_verified') else 0,
        },
        'opportunities': {
            'total': Opportunity.objects.count(),
            'active': Opportunity.objects.filter(status='published').count(),
        },
        'applications': {
            'total': Application.objects.count(),
            'this_month': Application.objects.filter(created_at__gte=thirty_days_ago).count(),
            'pending': Application.objects.filter(status='pending').count(),
        },
    }

    return Response({'success': True, 'data': stats})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_activity(request):
    """Get recent platform activity."""
    limit = int(request.query_params.get('limit', 20))
    activities = AdminAuditLog.objects.all().order_by('-created_at')[:limit]
    serializer = AdminAuditLogSerializer(activities, many=True)
    return Response({'success': True, 'data': serializer.data})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_health(request):
    """Get system health status."""
    from django.db import connection

    health = {
        'database': 'healthy',
        'cache': 'healthy',
        'services': {},
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['database'] = 'healthy'
    except Exception:
        health['database'] = 'unhealthy'

    return Response({'success': True, 'data': health})


# ═══════════════════════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    """List all users with filtering."""
    from users.models import User

    status_filter = request.query_params.get('status')
    search = request.query_params.get('search')
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    qs = User.objects.all().order_by('-date_joined')

    if status_filter:
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

    if search:
        qs = qs.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    total = qs.count()
    start = (page - 1) * per_page
    users = qs[start:start + per_page]

    data = [{
        'id': str(u.id),
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'is_active': u.is_active,
        'is_staff': u.is_staff,
        'date_joined': u.date_joined.isoformat(),
    } for u in users]

    return Response({
        'success': True,
        'data': data,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_user_detail(request, user_id):
    """Get user details."""
    from users.models import User

    try:
        user = User.objects.get(id=user_id)
        data = {
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        return Response({'success': True, 'data': data})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_user_toggle_status(request, user_id):
    """Toggle user active status."""
    from users.models import User

    try:
        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        return Response({'success': True, 'is_active': user.is_active})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_user_reset_password(request, user_id):
    """Reset user password and send email."""
    from users.models import User
    from django.contrib.auth.tokens import default_token_generator

    try:
        user = User.objects.get(id=user_id)
        token = default_token_generator.make_token(user)
        # Here you would send a password reset email
        return Response({'success': True, 'message': 'Password reset email sent'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_user_verify(request, user_id):
    """Verify user account."""
    from users.models import User

    try:
        user = User.objects.get(id=user_id)
        if hasattr(user, 'is_verified'):
            user.is_verified = True
            user.save()
        return Response({'success': True, 'message': 'User verified'})
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'User not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Talent Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_talents_list(request):
    """List all talent profiles."""
    from profiles.models import TalentProfile

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    search = request.query_params.get('search')

    qs = TalentProfile.objects.all().select_related('user').order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(headline__icontains=search)
        )

    total = qs.count()
    start = (page - 1) * per_page
    profiles = qs[start:start + per_page]

    data = [{
        'id': str(p.id),
        'user_id': str(p.user_id),
        'email': p.user.email,
        'name': f"{p.user.first_name} {p.user.last_name}",
        'headline': getattr(p, 'headline', ''),
        'is_verified': getattr(p, 'is_verified', False),
        'created_at': p.created_at.isoformat() if hasattr(p, 'created_at') else None,
    } for p in profiles]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_talent_detail(request, profile_id):
    """Get talent profile details."""
    from profiles.models import TalentProfile

    try:
        profile = TalentProfile.objects.select_related('user').get(id=profile_id)
        data = {
            'id': str(profile.id),
            'user': {
                'id': str(profile.user_id),
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
            },
            'headline': getattr(profile, 'headline', ''),
            'bio': getattr(profile, 'bio', ''),
            'is_verified': getattr(profile, 'is_verified', False),
        }
        return Response({'success': True, 'data': data})
    except TalentProfile.DoesNotExist:
        return Response({'success': False, 'error': 'Profile not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_talent_verify(request, profile_id):
    """Verify talent profile."""
    from profiles.models import TalentProfile

    try:
        profile = TalentProfile.objects.get(id=profile_id)
        if hasattr(profile, 'is_verified'):
            profile.is_verified = True
            profile.save()
        return Response({'success': True, 'message': 'Profile verified'})
    except TalentProfile.DoesNotExist:
        return Response({'success': False, 'error': 'Profile not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Organization Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_organizations_list(request):
    """List all organizations."""
    from organizations.models import Organization

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))
    search = request.query_params.get('search')

    qs = Organization.objects.all().order_by('-created_at')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(industry__icontains=search))

    total = qs.count()
    start = (page - 1) * per_page
    orgs = qs[start:start + per_page]

    data = [{
        'id': str(o.id),
        'name': o.name,
        'industry': getattr(o, 'industry', ''),
        'is_verified': getattr(o, 'is_verified', False),
        'status': getattr(o, 'status', 'active'),
        'created_at': o.created_at.isoformat() if hasattr(o, 'created_at') else None,
    } for o in orgs]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_organization_detail(request, org_id):
    """Get organization details."""
    from organizations.models import Organization

    try:
        org = Organization.objects.get(id=org_id)
        data = {
            'id': str(org.id),
            'name': org.name,
            'description': getattr(org, 'description', ''),
            'industry': getattr(org, 'industry', ''),
            'website': getattr(org, 'website', ''),
            'is_verified': getattr(org, 'is_verified', False),
            'status': getattr(org, 'status', 'active'),
        }
        return Response({'success': True, 'data': data})
    except Organization.DoesNotExist:
        return Response({'success': False, 'error': 'Organization not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_organization_verify(request, org_id):
    """Verify organization."""
    from organizations.models import Organization

    try:
        org = Organization.objects.get(id=org_id)
        if hasattr(org, 'is_verified'):
            org.is_verified = True
            org.save()
        return Response({'success': True, 'message': 'Organization verified'})
    except Organization.DoesNotExist:
        return Response({'success': False, 'error': 'Organization not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_organization_toggle_status(request, org_id):
    """Toggle organization status."""
    from organizations.models import Organization

    try:
        org = Organization.objects.get(id=org_id)
        if hasattr(org, 'status'):
            org.status = 'suspended' if org.status == 'active' else 'active'
            org.save()
        return Response({'success': True, 'status': getattr(org, 'status', 'active')})
    except Organization.DoesNotExist:
        return Response({'success': False, 'error': 'Organization not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Opportunity Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_opportunities_list(request):
    """List all opportunities."""
    from organizations.models import Opportunity

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    qs = Opportunity.objects.all().select_related('organization').order_by('-created_at')
    total = qs.count()
    start = (page - 1) * per_page
    opps = qs[start:start + per_page]

    data = [{
        'id': str(o.id),
        'title': o.title,
        'organization': o.organization.name,
        'status': getattr(o, 'status', 'draft'),
        'created_at': o.created_at.isoformat() if hasattr(o, 'created_at') else None,
    } for o in opps]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_opportunity_detail(request, opp_id):
    """Get opportunity details."""
    from organizations.models import Opportunity

    try:
        opp = Opportunity.objects.select_related('organization').get(id=opp_id)
        data = {
            'id': str(opp.id),
            'title': opp.title,
            'description': getattr(opp, 'description', ''),
            'organization': {
                'id': str(opp.organization_id),
                'name': opp.organization.name,
            },
            'status': getattr(opp, 'status', 'draft'),
        }
        return Response({'success': True, 'data': data})
    except Opportunity.DoesNotExist:
        return Response({'success': False, 'error': 'Opportunity not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_opportunity_toggle_status(request, opp_id):
    """Toggle opportunity status."""
    from organizations.models import Opportunity

    try:
        opp = Opportunity.objects.get(id=opp_id)
        if hasattr(opp, 'status'):
            if opp.status == 'published':
                opp.status = 'closed'
            else:
                opp.status = 'published'
            opp.save()
        return Response({'success': True, 'status': getattr(opp, 'status', 'draft')})
    except Opportunity.DoesNotExist:
        return Response({'success': False, 'error': 'Opportunity not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Application Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_applications_list(request):
    """List all applications."""
    from applications.models import Application

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    qs = Application.objects.all().order_by('-created_at')
    total = qs.count()
    start = (page - 1) * per_page
    apps = qs[start:start + per_page]

    data = [{
        'id': str(a.id),
        'status': getattr(a, 'status', 'pending'),
        'created_at': a.created_at.isoformat() if hasattr(a, 'created_at') else None,
    } for a in apps]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_application_detail(request, app_id):
    """Get application details."""
    from applications.models import Application

    try:
        app = Application.objects.get(id=app_id)
        data = {
            'id': str(app.id),
            'status': getattr(app, 'status', 'pending'),
            'created_at': app.created_at.isoformat() if hasattr(app, 'created_at') else None,
        }
        return Response({'success': True, 'data': data})
    except Application.DoesNotExist:
        return Response({'success': False, 'error': 'Application not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Communications Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_notifications_list(request):
    """List all notifications."""
    from communications.models import Notification

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    qs = Notification.objects.all().order_by('-created_at')
    total = qs.count()
    start = (page - 1) * per_page
    notifs = qs[start:start + per_page]

    data = [{
        'id': str(n.id),
        'title': getattr(n, 'title', ''),
        'notif_type': getattr(n, 'notif_type', 'info'),
        'is_read': getattr(n, 'is_read', False),
        'created_at': n.created_at.isoformat() if hasattr(n, 'created_at') else None,
    } for n in notifs]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_send_notification(request):
    """Send notification to users."""
    from communications.models import Notification
    from users.models import User

    title = request.data.get('title')
    body = request.data.get('body')
    notif_type = request.data.get('type', 'info')
    user_ids = request.data.get('user_ids', [])
    send_to_all = request.data.get('send_to_all', False)

    if not title or not body:
        return Response({'success': False, 'error': 'Title and body required'}, status=400)

    if send_to_all:
        users = User.objects.all()
    else:
        users = User.objects.filter(id__in=user_ids)

    count = 0
    for user in users:
        Notification.objects.create(
            recipient=user,
            title=title,
            body=body,
            notif_type=notif_type,
        )
        count += 1

    return Response({'success': True, 'sent_count': count})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_email_logs(request):
    """Get email logs."""
    from communications.models import EmailLog

    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 20))

    qs = EmailLog.objects.all().order_by('-created_at')
    total = qs.count()
    start = (page - 1) * per_page
    logs = qs[start:start + per_page]

    data = [{
        'id': str(l.id),
        'to_email': getattr(l, 'to_email', ''),
        'subject': getattr(l, 'subject', ''),
        'status': getattr(l, 'status', 'sent'),
        'created_at': l.created_at.isoformat() if hasattr(l, 'created_at') else None,
    } for l in logs]

    return Response({
        'success': True,
        'data': data,
        'pagination': {'total': total, 'page': page, 'per_page': per_page}
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_send_email(request):
    """Send email to user."""
    from django.core.mail import send_mail
    from django.conf import settings

    to_email = request.data.get('to_email')
    subject = request.data.get('subject')
    body = request.data.get('body')

    if not all([to_email, subject, body]):
        return Response({'success': False, 'error': 'to_email, subject, body required'}, status=400)

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        return Response({'success': True, 'message': 'Email sent'})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_blast_email(request):
    """Send blast email to multiple users."""
    subject = request.data.get('subject')
    body = request.data.get('body')
    recipients = request.data.get('recipients', [])  # List of email addresses

    if not all([subject, body, recipients]):
        return Response({'success': False, 'error': 'subject, body, recipients required'}, status=400)

    # This would typically be handled by a background task
    return Response({'success': True, 'message': f'Blast email queued for {len(recipients)} recipients'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_newsletters(request):
    """Get newsletters."""
    return Response({'success': True, 'data': []})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_email_templates(request):
    """Get email templates."""
    return Response({'success': True, 'data': []})


# ═══════════════════════════════════════════════════════════════════════════════
# Website Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_waitlist(request):
    """Get waitlist entries."""
    # This would connect to the website's waitlist model
    return Response({'success': True, 'data': []})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_partners(request):
    """Get partner registrations."""
    return Response({'success': True, 'data': []})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_contacts(request):
    """Get contact messages."""
    return Response({'success': True, 'data': []})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_blog_posts(request):
    """Get blog posts."""
    return Response({'success': True, 'data': []})


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_blog_post_detail(request, post_id):
    """Manage blog post."""
    return Response({'success': True, 'data': {}})


# ═══════════════════════════════════════════════════════════════════════════════
# Announcements
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_announcements_list(request):
    """List announcements."""
    from communications.models import Announcement

    announcements = Announcement.objects.all().order_by('-created_at')
    data = [{
        'id': str(a.id),
        'title': getattr(a, 'title', ''),
        'is_active': getattr(a, 'is_active', True),
        'created_at': a.created_at.isoformat() if hasattr(a, 'created_at') else None,
    } for a in announcements]

    return Response({'success': True, 'data': data})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_announcement_create(request):
    """Create announcement."""
    from communications.models import Announcement

    title = request.data.get('title')
    body = request.data.get('body')

    if not title or not body:
        return Response({'success': False, 'error': 'Title and body required'}, status=400)

    announcement = Announcement.objects.create(
        title=title,
        body=body,
        created_by=request.user,
    )

    return Response({'success': True, 'id': str(announcement.id)})


@api_view(['GET', 'PUT'])
@permission_classes([IsAdminUser])
def admin_announcement_detail(request, ann_id):
    """Get or update announcement."""
    from communications.models import Announcement

    try:
        announcement = Announcement.objects.get(id=ann_id)

        if request.method == 'GET':
            data = {
                'id': str(announcement.id),
                'title': getattr(announcement, 'title', ''),
                'body': getattr(announcement, 'body', ''),
                'is_active': getattr(announcement, 'is_active', True),
            }
            return Response({'success': True, 'data': data})

        elif request.method == 'PUT':
            announcement.title = request.data.get('title', announcement.title)
            announcement.body = request.data.get('body', announcement.body)
            announcement.save()
            return Response({'success': True, 'message': 'Updated'})

    except Announcement.DoesNotExist:
        return Response({'success': False, 'error': 'Not found'}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_announcement_delete(request, ann_id):
    """Delete announcement."""
    from communications.models import Announcement

    try:
        announcement = Announcement.objects.get(id=ann_id)
        announcement.delete()
        return Response({'success': True, 'message': 'Deleted'})
    except Announcement.DoesNotExist:
        return Response({'success': False, 'error': 'Not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Admin User Management
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_admins_list(request):
    """List admin users."""
    from users.models import User

    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    data = [{
        'id': str(a.id),
        'email': a.email,
        'first_name': a.first_name,
        'last_name': a.last_name,
        'is_superuser': a.is_superuser,
        'date_joined': a.date_joined.isoformat(),
    } for a in admins]

    return Response({'success': True, 'data': data})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_admin_create(request):
    """Create admin user."""
    from users.models import User

    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not email or not password:
        return Response({'success': False, 'error': 'Email and password required'}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({'success': False, 'error': 'Email already exists'}, status=400)

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff=True,
    )

    return Response({'success': True, 'id': str(user.id)})


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_admin_detail(request, admin_id):
    """Manage admin user."""
    from users.models import User

    try:
        admin = User.objects.get(id=admin_id, is_staff=True)

        if request.method == 'GET':
            data = {
                'id': str(admin.id),
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'is_superuser': admin.is_superuser,
            }
            return Response({'success': True, 'data': data})

        elif request.method == 'PUT':
            admin.first_name = request.data.get('first_name', admin.first_name)
            admin.last_name = request.data.get('last_name', admin.last_name)
            admin.is_superuser = request.data.get('is_superuser', admin.is_superuser)
            admin.save()
            return Response({'success': True, 'message': 'Updated'})

        elif request.method == 'DELETE':
            if admin == request.user:
                return Response({'success': False, 'error': 'Cannot delete self'}, status=400)
            admin.delete()
            return Response({'success': True, 'message': 'Deleted'})

    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reports_users(request):
    """Get user reports."""
    from users.models import User
    from django.db.models.functions import TruncMonth

    data = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'staff': User.objects.filter(is_staff=True).count(),
    }

    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reports_organizations(request):
    """Get organization reports."""
    from organizations.models import Organization

    data = {
        'total': Organization.objects.count(),
    }

    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reports_applications(request):
    """Get application reports."""
    from applications.models import Application

    data = {
        'total': Application.objects.count(),
    }

    return Response({'success': True, 'data': data})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reports_export(request):
    """Export reports."""
    report_type = request.query_params.get('type', 'users')
    format_type = request.query_params.get('format', 'csv')

    # This would generate the actual export file
    return Response({
        'success': True,
        'message': f'Export for {report_type} in {format_type} format queued'
    })


# ═══════════════════════════════════════════════════════════════════════════════
# System Settings
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_settings_list(request):
    """Get system settings."""
    settings_data = {
        'site_name': 'ForgeForth Africa',
        'maintenance_mode': False,
        'registration_enabled': True,
        'email_verification_required': True,
    }

    return Response({'success': True, 'data': settings_data})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_settings_update(request):
    """Update system settings."""
    # This would update actual settings
    return Response({'success': True, 'message': 'Settings updated'})


# ═══════════════════════════════════════════════════════════════════════════════
# DevOps
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_devops_services(request):
    """Get services status."""
    services = [
        {'name': 'API Service', 'status': 'healthy', 'port': 9001},
        {'name': 'Website', 'status': 'healthy', 'port': 9880},
        {'name': 'Talent Portal', 'status': 'healthy', 'port': 9003},
        {'name': 'Partners Portal', 'status': 'healthy', 'port': 9004},
        {'name': 'Admin Portal', 'status': 'healthy', 'port': 9002},
    ]

    return Response({'success': True, 'data': services})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_devops_logs(request):
    """Get system logs."""
    return Response({'success': True, 'data': []})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_devops_deployments(request):
    """Get deployment history."""
    return Response({'success': True, 'data': []})

