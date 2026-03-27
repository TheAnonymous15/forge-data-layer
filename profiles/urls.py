# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Profiles URLs
=============================================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'profiles'

router = DefaultRouter()
router.register(r'profiles', views.TalentProfileViewSet, basename='profile')
router.register(r'skills', views.SkillViewSet, basename='skill')
router.register(r'talent-skills', views.TalentSkillViewSet, basename='talent-skill')
router.register(r'education', views.EducationViewSet, basename='education')
router.register(r'experience', views.WorkExperienceViewSet, basename='experience')
router.register(r'certifications', views.CertificationViewSet, basename='certification')
router.register(r'languages', views.LanguageViewSet, basename='language')
router.register(r'connections', views.ConnectionViewSet, basename='connection')
router.register(r'mentors', views.MentorViewSet, basename='mentor')
router.register(r'goals', views.GoalViewSet, basename='goal')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.profiles_stats, name='profiles-stats'),
    path('skills/stats/', views.skills_stats, name='skills-stats'),
    
    # Connection endpoints
    path('connections/requests/', views.connection_requests, name='connection-requests'),
    path('connections/suggestions/', views.connection_suggestions, name='connection-suggestions'),
    path('connections/<uuid:user_id>/connect/', views.connection_send_request, name='connection-send-request'),
    path('connections/<uuid:pk>/accept/', views.connection_accept, name='connection-accept'),
    path('connections/<uuid:pk>/decline/', views.connection_decline, name='connection-decline'),
    
    # Mentor endpoints
    path('mentors/search/', views.mentor_search, name='mentor-search'),
    path('mentors/become/', views.become_mentor, name='become-mentor'),
    path('mentors/my-mentors/', views.my_mentors, name='my-mentors'),
    path('mentors/my-mentees/', views.my_mentees, name='my-mentees'),
    path('mentors/<uuid:mentor_id>/request/', views.mentor_request, name='mentor-request'),
    path('mentors/requests/<uuid:request_id>/accept/', views.mentor_request_accept, name='mentor-request-accept'),
    path('mentors/requests/<uuid:request_id>/decline/', views.mentor_request_decline, name='mentor-request-decline'),
    
    # Progress & Goals
    path('progress/', views.progress_overview, name='progress-overview'),
    path('progress/stats/', views.progress_stats, name='progress-stats'),
    path('goals/<uuid:pk>/complete/', views.goal_complete, name='goal-complete'),
    
    # Activities & Contributions
    path('activities/', views.activity_list, name='activity-list'),
    path('activities/log/', views.activity_log, name='activity-log'),
    path('contributions/', views.contribution_list, name='contribution-list'),
    
    # Learning & Development
    path('learning/', views.learning_overview, name='learning-overview'),
    path('learning/courses/', views.learning_courses, name='learning-courses'),
    path('learning/courses/<uuid:course_id>/', views.learning_course_detail, name='learning-course-detail'),
    path('learning/courses/<uuid:course_id>/enroll/', views.learning_course_enroll, name='learning-course-enroll'),
    path('learning/courses/<uuid:course_id>/progress/', views.learning_course_progress, name='learning-course-progress'),
    path('learning/recommendations/', views.learning_recommendations, name='learning-recommendations'),
]
