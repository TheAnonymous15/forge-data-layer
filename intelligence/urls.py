# -*- coding: utf-8 -*-
"""Intelligence API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'intelligence'

router = DefaultRouter()
router.register(r'skills-taxonomy', views.SkillTaxonomyViewSet, basename='skill-taxonomy')
router.register(r'cv-parse', views.CVParseResultViewSet, basename='cv-parse')
router.register(r'talent-scores', views.TalentScoreViewSet, basename='talent-score')
router.register(r'insights', views.IntelligenceInsightViewSet, basename='insight')

urlpatterns = [
    path('', include(router.urls)),
]

