# -*- coding: utf-8 -*-
"""Administration API URLs - Comprehensive Admin Endpoints."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'administration'

router = DefaultRouter()
router.register(r'roles', views.StaffRoleViewSet, basename='role')
router.register(r'role-assignments', views.StaffRoleAssignmentViewSet, basename='role-assignment')
router.register(r'feature-flags', views.FeatureFlagViewSet, basename='feature-flag')
router.register(r'audit-logs', views.AdminAuditLogViewSet, basename='audit-log')
router.register(r'support-tickets', views.SupportTicketViewSet, basename='support-ticket')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # ─────────────────────────────────────────────────────────
    # Dashboard & Statistics
    # ─────────────────────────────────────────────────────────
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/recent-activity/', views.recent_activity, name='recent-activity'),
    path('dashboard/system-health/', views.system_health, name='system-health'),

    # ─────────────────────────────────────────────────────────
    # User Management
    # ─────────────────────────────────────────────────────────
    path('users/', views.admin_users_list, name='admin-users-list'),
    path('users/<uuid:user_id>/', views.admin_user_detail, name='admin-user-detail'),
    path('users/<uuid:user_id>/toggle-status/', views.admin_user_toggle_status, name='admin-user-toggle-status'),
    path('users/<uuid:user_id>/reset-password/', views.admin_user_reset_password, name='admin-user-reset-password'),
    path('users/<uuid:user_id>/verify/', views.admin_user_verify, name='admin-user-verify'),

    # ─────────────────────────────────────────────────────────
    # Talent Management
    # ─────────────────────────────────────────────────────────
    path('talents/', views.admin_talents_list, name='admin-talents-list'),
    path('talents/<uuid:profile_id>/', views.admin_talent_detail, name='admin-talent-detail'),
    path('talents/<uuid:profile_id>/verify/', views.admin_talent_verify, name='admin-talent-verify'),

    # ─────────────────────────────────────────────────────────
    # Organization Management
    # ─────────────────────────────────────────────────────────
    path('organizations/', views.admin_organizations_list, name='admin-organizations-list'),
    path('organizations/<uuid:org_id>/', views.admin_organization_detail, name='admin-organization-detail'),
    path('organizations/<uuid:org_id>/verify/', views.admin_organization_verify, name='admin-organization-verify'),
    path('organizations/<uuid:org_id>/toggle-status/', views.admin_organization_toggle_status, name='admin-organization-toggle-status'),

    # ─────────────────────────────────────────────────────────
    # Opportunity Management
    # ─────────────────────────────────────────────────────────
    path('opportunities/', views.admin_opportunities_list, name='admin-opportunities-list'),
    path('opportunities/<uuid:opp_id>/', views.admin_opportunity_detail, name='admin-opportunity-detail'),
    path('opportunities/<uuid:opp_id>/toggle-status/', views.admin_opportunity_toggle_status, name='admin-opportunity-toggle-status'),

    # ─────────────────────────────────────────────────────────
    # Application Management
    # ─────────────────────────────────────────────────────────
    path('applications/', views.admin_applications_list, name='admin-applications-list'),
    path('applications/<uuid:app_id>/', views.admin_application_detail, name='admin-application-detail'),

    # ─────────────────────────────────────────────────────────
    # Communications Management
    # ─────────────────────────────────────────────────────────
    path('communications/notifications/', views.admin_notifications_list, name='admin-notifications-list'),
    path('communications/send-notification/', views.admin_send_notification, name='admin-send-notification'),
    path('communications/email-logs/', views.admin_email_logs, name='admin-email-logs'),
    path('communications/send-email/', views.admin_send_email, name='admin-send-email'),
    path('communications/blast-email/', views.admin_blast_email, name='admin-blast-email'),
    path('communications/newsletters/', views.admin_newsletters, name='admin-newsletters'),
    path('communications/templates/', views.admin_email_templates, name='admin-email-templates'),

    # ─────────────────────────────────────────────────────────
    # Website Management
    # ─────────────────────────────────────────────────────────
    path('website/waitlist/', views.admin_waitlist, name='admin-waitlist'),
    path('website/partners/', views.admin_partners, name='admin-partners'),
    path('website/contacts/', views.admin_contacts, name='admin-contacts'),
    path('website/blog/', views.admin_blog_posts, name='admin-blog-posts'),
    path('website/blog/<uuid:post_id>/', views.admin_blog_post_detail, name='admin-blog-post-detail'),

    # ─────────────────────────────────────────────────────────
    # Announcements
    # ─────────────────────────────────────────────────────────
    path('announcements/', views.admin_announcements_list, name='admin-announcements-list'),
    path('announcements/create/', views.admin_announcement_create, name='admin-announcement-create'),
    path('announcements/<uuid:ann_id>/', views.admin_announcement_detail, name='admin-announcement-detail'),
    path('announcements/<uuid:ann_id>/delete/', views.admin_announcement_delete, name='admin-announcement-delete'),

    # ─────────────────────────────────────────────────────────
    # Admin User Management
    # ─────────────────────────────────────────────────────────
    path('admin-users/', views.admin_admins_list, name='admin-admins-list'),
    path('admin-users/create/', views.admin_admin_create, name='admin-admin-create'),
    path('admin-users/<uuid:admin_id>/', views.admin_admin_detail, name='admin-admin-detail'),

    # ─────────────────────────────────────────────────────────
    # Reports & Export
    # ─────────────────────────────────────────────────────────
    path('reports/users/', views.admin_reports_users, name='admin-reports-users'),
    path('reports/organizations/', views.admin_reports_organizations, name='admin-reports-organizations'),
    path('reports/applications/', views.admin_reports_applications, name='admin-reports-applications'),
    path('reports/export/', views.admin_reports_export, name='admin-reports-export'),

    # ─────────────────────────────────────────────────────────
    # System Settings
    # ─────────────────────────────────────────────────────────
    path('settings/', views.admin_settings_list, name='admin-settings-list'),
    path('settings/update/', views.admin_settings_update, name='admin-settings-update'),

    # ─────────────────────────────────────────────────────────
    # DevOps
    # ─────────────────────────────────────────────────────────
    path('devops/services/', views.admin_devops_services, name='admin-devops-services'),
    path('devops/logs/', views.admin_devops_logs, name='admin-devops-logs'),
    path('devops/deployments/', views.admin_devops_deployments, name='admin-devops-deployments'),
]
