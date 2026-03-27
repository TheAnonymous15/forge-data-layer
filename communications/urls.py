# -*- coding: utf-8 -*-
"""
Communications API URLs
=======================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'communications'

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'email-logs', views.EmailLogViewSet, basename='email-log')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'announcements', views.AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.communications_stats, name='communications-stats'),
    path('send-notification/', views.send_notification, name='send-notification'),
]

