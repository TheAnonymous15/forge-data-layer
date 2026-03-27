# -*- coding: utf-8 -*-
"""Matching API Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MatchScore, Recommendation
from .serializers import MatchScoreSerializer, RecommendationSerializer


class MatchScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for match scores."""
    serializer_class = MatchScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MatchScore.objects.filter(user=self.request.user).select_related('opportunity__organization')

    @action(detail=False, methods=['get'])
    def top_matches(self, request):
        """Get top matching opportunities."""
        matches = self.get_queryset().filter(overall_score__gte=70).order_by('-overall_score')[:10]
        return Response({'success': True, 'data': MatchScoreSerializer(matches, many=True).data})

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate match score for a specific opportunity."""
        opportunity_id = request.data.get('opportunity_id')
        if not opportunity_id:
            return Response({'success': False, 'error': 'opportunity_id required'}, status=400)

        # Placeholder - actual calculation would be more complex
        score, created = MatchScore.objects.get_or_create(
            user=request.user,
            opportunity_id=opportunity_id,
            defaults={'overall_score': 0.0}
        )
        return Response({'success': True, 'data': MatchScoreSerializer(score).data})


class RecommendationViewSet(viewsets.ModelViewSet):
    """API endpoint for recommendations."""
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Recommendation.objects.filter(user=self.request.user, is_dismissed=False)

    @action(detail=False, methods=['get'])
    def opportunities(self, request):
        """Get opportunity recommendations."""
        recs = self.get_queryset().filter(rec_type='opportunity').order_by('-relevance_score')[:20]
        return Response({'success': True, 'data': RecommendationSerializer(recs, many=True).data})

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a recommendation."""
        rec = self.get_object()
        rec.is_dismissed = True
        rec.save()
        return Response({'success': True})

    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """Track recommendation click."""
        rec = self.get_object()
        rec.is_clicked = True
        rec.is_viewed = True
        rec.save()
        return Response({'success': True})

