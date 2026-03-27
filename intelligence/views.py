# -*- coding: utf-8 -*-
"""Intelligence API Views."""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SkillTaxonomy, CVParseResult, TalentScore, SkillExtraction, IntelligenceInsight
from .serializers import (
    SkillTaxonomySerializer, CVParseResultSerializer, TalentScoreSerializer,
    SkillExtractionSerializer, IntelligenceInsightSerializer
)

logger = logging.getLogger('api_service.intelligence')


class SkillTaxonomyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for skill taxonomy."""
    queryset = SkillTaxonomy.objects.all()
    serializer_class = SkillTaxonomySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending skills."""
        skills = self.queryset.filter(trend='rising').order_by('-demand_score')[:20]
        return Response({'success': True, 'data': SkillTaxonomySerializer(skills, many=True).data})


class CVParseResultViewSet(viewsets.ModelViewSet):
    """API endpoint for CV parsing."""
    serializer_class = CVParseResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CVParseResult.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def parse(self, request):
        """Parse a CV/resume file."""
        file_url = request.data.get('file_url')
        if not file_url:
            return Response({'success': False, 'error': 'file_url is required'}, status=400)

        # Create parse result (actual parsing would be async)
        result = CVParseResult.objects.create(
            user=request.user,
            source_file_url=file_url,
            source_file_name=file_url.split('/')[-1],
            status='processing'
        )

        return Response({
            'success': True,
            'message': 'CV parsing initiated',
            'data': CVParseResultSerializer(result).data
        })


class TalentScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for talent scores."""
    serializer_class = TalentScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TalentScore.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get', 'post'])
    def my_score(self, request):
        """Get or calculate current user's talent score."""
        score, created = TalentScore.objects.get_or_create(user=request.user)
        return Response({'success': True, 'data': TalentScoreSerializer(score).data})


class IntelligenceInsightViewSet(viewsets.ModelViewSet):
    """API endpoint for AI insights."""
    serializer_class = IntelligenceInsightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return IntelligenceInsight.objects.filter(user=self.request.user, is_dismissed=False)

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss an insight."""
        insight = self.get_object()
        insight.is_dismissed = True
        from django.utils import timezone
        insight.dismissed_at = timezone.now()
        insight.save()
        return Response({'success': True})

