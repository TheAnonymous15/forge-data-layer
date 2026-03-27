# -*- coding: utf-8 -*-
"""Intelligence Serializers."""
from rest_framework import serializers
from .models import SkillTaxonomy, CVParseResult, TalentScore, SkillExtraction, IntelligenceInsight


class SkillTaxonomySerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillTaxonomy
        fields = ['id', 'name', 'normalized_name', 'category', 'aliases', 'related_skills', 'demand_score', 'trend']


class CVParseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVParseResult
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


class TalentScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentScore
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'calculated_at']


class SkillExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillExtraction
        fields = ['id', 'source_text', 'source_type', 'extracted_skills', 'confidence_scores', 'processing_time_ms', 'created_at']
        read_only_fields = ['id', 'extracted_skills', 'confidence_scores', 'processing_time_ms', 'created_at']


class IntelligenceInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntelligenceInsight
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

