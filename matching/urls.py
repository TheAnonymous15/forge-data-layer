# -*- coding: utf-8 -*-
"""Matching API URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'matching'

router = DefaultRouter()
router.register(r'scores', views.MatchScoreViewSet, basename='score')
router.register(r'recommendations', views.RecommendationViewSet, basename='recommendation')

urlpatterns = [
    path('', include(router.urls)),
]

