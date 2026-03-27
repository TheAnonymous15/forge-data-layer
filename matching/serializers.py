# -*- coding: utf-8 -*-
"""Matching Serializers."""
from rest_framework import serializers
from .models import MatchScore, Recommendation, SearchIndex


class MatchScoreSerializer(serializers.ModelSerializer):
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    organization_name = serializers.CharField(source='opportunity.organization.name', read_only=True)

    class Meta:
        model = MatchScore
        fields = '__all__'


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


class SearchIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchIndex
        fields = ['id', 'entity_type', 'entity_id', 'keywords', 'skills', 'is_active', 'last_indexed']

