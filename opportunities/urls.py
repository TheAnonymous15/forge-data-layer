# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Opportunities URLs
=================================================
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'opportunities'

router = DefaultRouter()
router.register(r'opportunities', views.OpportunityViewSet, basename='opportunity')
router.register(r'saved', views.SavedOpportunityViewSet, basename='saved-opportunity')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', views.opportunities_stats, name='opportunities-stats'),
    path('by-slug/<slug:slug>/', views.opportunity_by_slug, name='opportunity-by-slug'),
]

