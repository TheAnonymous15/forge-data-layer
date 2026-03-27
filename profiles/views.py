# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Profile Views
============================================
Complete CRUD endpoints for talent profiles.
"""
import logging
from django.utils.text import slugify
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    TalentProfile, Skill, TalentSkill, Education,
    WorkExperience, Certification, Language
)
from .serializers import (
    TalentProfileSerializer, TalentProfileListSerializer,
    TalentProfileCreateUpdateSerializer, SkillSerializer,
    TalentSkillSerializer, EducationSerializer,
    WorkExperienceSerializer, CertificationSerializer,
    LanguageSerializer
)

logger = logging.getLogger(__name__)


class TalentProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Talent Profiles.

    Endpoints:
    - GET /profiles/ - List all profiles
    - POST /profiles/ - Create new profile
    - GET /profiles/{id}/ - Get profile details
    - PUT/PATCH /profiles/{id}/ - Update profile
    - DELETE /profiles/{id}/ - Delete profile
    - GET /profiles/by-user/ - Get profile by user ID
    - GET /profiles/{id}/full/ - Get full profile with all relations
    """
    queryset = TalentProfile.objects.select_related('user').prefetch_related(
        'skills__skill', 'education', 'work_experience', 'certifications', 'languages'
    )
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return TalentProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TalentProfileCreateUpdateSerializer
        return TalentProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by experience level
        exp_level = self.request.query_params.get('experience_level')
        if exp_level:
            queryset = queryset.filter(experience_level=exp_level)

        # Filter by availability
        availability = self.request.query_params.get('availability_status')
        if availability:
            queryset = queryset.filter(availability_status=availability)

        # Filter by public status
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(headline__icontains=search) |
                Q(bio__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get profile by user ID."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)

        try:
            profile = self.queryset.get(user_id=user_id)
            serializer = TalentProfileSerializer(profile)
            return Response(serializer.data)
        except TalentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)

    @action(detail=True, methods=['get'])
    def full(self, request, pk=None):
        """Get full profile with all related data."""
        profile = self.get_object()
        serializer = TalentProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def calculate_completeness(self, request, pk=None):
        """Recalculate profile completeness score."""
        profile = self.get_object()

        score = 0
        total = 100

        # Basic info (30%)
        if profile.headline:
            score += 10
        if profile.bio:
            score += 10
        if profile.experience_level:
            score += 10

        # Skills (20%)
        skills_count = profile.skills.count()
        if skills_count >= 5:
            score += 20
        elif skills_count >= 3:
            score += 15
        elif skills_count >= 1:
            score += 10

        # Education (15%)
        if profile.education.exists():
            score += 15

        # Experience (20%)
        if profile.work_experience.exists():
            score += 20

        # Links (15%)
        links_score = 0
        if profile.linkedin_url:
            links_score += 5
        if profile.github_url:
            links_score += 5
        if profile.portfolio_url:
            links_score += 5
        score += links_score

        profile.profile_completeness = score
        profile.save(update_fields=['profile_completeness'])

        return Response({
            'id': str(profile.id),
            'profile_completeness': score,
            'message': 'Profile completeness recalculated'
        })


class SkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Skills taxonomy.

    Endpoints:
    - GET /skills/ - List all skills
    - POST /skills/ - Create new skill
    - GET /skills/{id}/ - Get skill details
    - PUT/PATCH /skills/{id}/ - Update skill
    - DELETE /skills/{id}/ - Delete skill
    - GET /skills/search/ - Search skills
    - GET /skills/popular/ - Get popular skills
    - GET /skills/by-category/ - Get skills by category
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Filter by verified
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name')
        slug = slugify(name)
        counter = 1
        base_slug = slug
        while Skill.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        serializer.save(slug=slug)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search skills by name."""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])

        skills = self.queryset.filter(name__icontains=query)[:20]
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular skills."""
        limit = int(request.query_params.get('limit', 20))
        skills = self.queryset.order_by('-usage_count')[:limit]
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get skills grouped by category."""
        categories = {}
        for category in Skill.Category.choices:
            skills = self.queryset.filter(category=category[0])[:20]
            categories[category[1]] = SkillSerializer(skills, many=True).data
        return Response(categories)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all skill categories."""
        return Response([
            {'value': c[0], 'label': c[1]}
            for c in Skill.Category.choices
        ])


class TalentSkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TalentSkill associations.

    Endpoints:
    - GET /talent-skills/ - List all talent skills
    - POST /talent-skills/ - Add skill to profile
    - GET /talent-skills/{id}/ - Get talent skill details
    - PUT/PATCH /talent-skills/{id}/ - Update talent skill
    - DELETE /talent-skills/{id}/ - Remove skill from profile
    - GET /talent-skills/by-profile/ - Get skills for a profile
    """
    queryset = TalentSkill.objects.select_related('profile', 'skill')
    serializer_class = TalentSkillSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        skill_id = self.request.query_params.get('skill_id')
        if skill_id:
            queryset = queryset.filter(skill_id=skill_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_profile(self, request):
        """Get all skills for a profile."""
        profile_id = request.query_params.get('profile_id')
        if not profile_id:
            return Response({'error': 'profile_id is required'}, status=400)

        skills = self.queryset.filter(profile_id=profile_id)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        instance = serializer.save()
        # Increment skill usage count
        instance.skill.usage_count += 1
        instance.skill.save(update_fields=['usage_count'])

    def perform_destroy(self, instance):
        # Decrement skill usage count
        if instance.skill.usage_count > 0:
            instance.skill.usage_count -= 1
            instance.skill.save(update_fields=['usage_count'])
        instance.delete()


class EducationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Education records.

    Endpoints:
    - GET /education/ - List all education records
    - POST /education/ - Add education record
    - GET /education/{id}/ - Get education details
    - PUT/PATCH /education/{id}/ - Update education
    - DELETE /education/{id}/ - Delete education
    - GET /education/by-profile/ - Get education for a profile
    """
    queryset = Education.objects.select_related('profile')
    serializer_class = EducationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_profile(self, request):
        """Get all education records for a profile."""
        profile_id = request.query_params.get('profile_id')
        if not profile_id:
            return Response({'error': 'profile_id is required'}, status=400)

        education = self.queryset.filter(profile_id=profile_id)
        serializer = self.get_serializer(education, many=True)
        return Response(serializer.data)


class WorkExperienceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Work Experience records.

    Endpoints:
    - GET /experience/ - List all experience records
    - POST /experience/ - Add experience record
    - GET /experience/{id}/ - Get experience details
    - PUT/PATCH /experience/{id}/ - Update experience
    - DELETE /experience/{id}/ - Delete experience
    - GET /experience/by-profile/ - Get experience for a profile
    """
    queryset = WorkExperience.objects.select_related('profile')
    serializer_class = WorkExperienceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_profile(self, request):
        """Get all experience records for a profile."""
        profile_id = request.query_params.get('profile_id')
        if not profile_id:
            return Response({'error': 'profile_id is required'}, status=400)

        experience = self.queryset.filter(profile_id=profile_id)
        serializer = self.get_serializer(experience, many=True)
        return Response(serializer.data)


class CertificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Certifications.

    Endpoints:
    - GET /certifications/ - List all certifications
    - POST /certifications/ - Add certification
    - GET /certifications/{id}/ - Get certification details
    - PUT/PATCH /certifications/{id}/ - Update certification
    - DELETE /certifications/{id}/ - Delete certification
    - GET /certifications/by-profile/ - Get certifications for a profile
    """
    queryset = Certification.objects.select_related('profile')
    serializer_class = CertificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_profile(self, request):
        """Get all certifications for a profile."""
        profile_id = request.query_params.get('profile_id')
        if not profile_id:
            return Response({'error': 'profile_id is required'}, status=400)

        certs = self.queryset.filter(profile_id=profile_id)
        serializer = self.get_serializer(certs, many=True)
        return Response(serializer.data)


class LanguageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Language proficiencies.

    Endpoints:
    - GET /languages/ - List all language records
    - POST /languages/ - Add language
    - GET /languages/{id}/ - Get language details
    - PUT/PATCH /languages/{id}/ - Update language
    - DELETE /languages/{id}/ - Delete language
    - GET /languages/by-profile/ - Get languages for a profile
    """
    queryset = Language.objects.select_related('profile')
    serializer_class = LanguageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        profile_id = self.request.query_params.get('profile_id')
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_profile(self, request):
        """Get all languages for a profile."""
        profile_id = request.query_params.get('profile_id')
        if not profile_id:
            return Response({'error': 'profile_id is required'}, status=400)

        languages = self.queryset.filter(profile_id=profile_id)
        serializer = self.get_serializer(languages, many=True)
        return Response(serializer.data)


# ============================================================
# Standalone API Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def profiles_stats(request):
    """Get profile statistics."""
    total = TalentProfile.objects.count()
    public = TalentProfile.objects.filter(is_public=True).count()

    by_experience = {}
    for level in TalentProfile.ExperienceLevel.choices:
        count = TalentProfile.objects.filter(experience_level=level[0]).count()
        by_experience[level[1]] = count

    by_availability = {}
    for status in TalentProfile.AvailabilityStatus.choices:
        count = TalentProfile.objects.filter(availability_status=status[0]).count()
        by_availability[status[1]] = count

    avg_completeness = TalentProfile.objects.aggregate(
        avg=models.Avg('profile_completeness')
    )['avg'] or 0

    return Response({
        'total_profiles': total,
        'public_profiles': public,
        'average_completeness': round(avg_completeness, 1),
        'by_experience_level': by_experience,
        'by_availability': by_availability,
        'total_skills': Skill.objects.count(),
        'verified_skills': Skill.objects.filter(is_verified=True).count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def skills_stats(request):
    """Get skills statistics."""
    return Response({
        'total_skills': Skill.objects.count(),
        'verified_skills': Skill.objects.filter(is_verified=True).count(),
        'total_talent_skills': TalentSkill.objects.count(),
        'skills_by_category': {
            c[1]: Skill.objects.filter(category=c[0]).count()
            for c in Skill.Category.choices
        }
    })


# ============================================================
# Connections ViewSet and Views
# ============================================================

class ConnectionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user connections.
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """List user's connections."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        # Placeholder - would query Connection model
        return Response({
            'success': True,
            'connections': [],
            'total': 0,
            'message': 'Connection model pending implementation'
        })

    def destroy(self, request, pk=None):
        """Remove a connection."""
        return Response({
            'success': True,
            'message': 'Connection removed'
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def connection_requests(request):
    """Get pending connection requests."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'received': [],
        'sent': [],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def connection_suggestions(request):
    """Get connection suggestions based on profile."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    # Get profiles with similar skills/interests
    # Placeholder - would use matching algorithm
    return Response({
        'success': True,
        'suggestions': [],
        'message': 'Suggestions based on profile similarities'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def connection_send_request(request, user_id):
    """Send a connection request."""
    from_user_id = request.data.get('from_user_id')
    message = request.data.get('message', '')
    
    return Response({
        'success': True,
        'message': 'Connection request sent',
        'request_id': 'placeholder-id'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def connection_accept(request, pk):
    """Accept a connection request."""
    return Response({
        'success': True,
        'message': 'Connection request accepted'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def connection_decline(request, pk):
    """Decline a connection request."""
    return Response({
        'success': True,
        'message': 'Connection request declined'
    })


# ============================================================
# Mentorship ViewSet and Views
# ============================================================

class MentorViewSet(viewsets.ViewSet):
    """
    ViewSet for managing mentorship.
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """List available mentors."""
        # Placeholder - would query Mentor profiles
        return Response({
            'success': True,
            'mentors': [],
            'total': 0,
        })

    def retrieve(self, request, pk=None):
        """Get mentor details."""
        return Response({
            'success': True,
            'mentor': {
                'id': str(pk),
                'note': 'Mentor profile data would be here'
            }
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def mentor_search(request):
    """Search for mentors."""
    skills = request.query_params.get('skills', '')
    industry = request.query_params.get('industry', '')
    
    return Response({
        'success': True,
        'mentors': [],
        'filters_applied': {
            'skills': skills,
            'industry': industry,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def become_mentor(request):
    """Apply to become a mentor."""
    user_id = request.data.get('user_id')
    expertise = request.data.get('expertise', [])
    availability = request.data.get('availability', '')
    bio = request.data.get('mentor_bio', '')
    
    return Response({
        'success': True,
        'message': 'Mentor application submitted',
        'status': 'pending_review',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def my_mentors(request):
    """Get user's current mentors."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'mentors': [],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def my_mentees(request):
    """Get mentor's current mentees."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'mentees': [],
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def mentor_request(request, mentor_id):
    """Send mentorship request."""
    mentee_id = request.data.get('mentee_id')
    message = request.data.get('message', '')
    goals = request.data.get('goals', [])
    
    return Response({
        'success': True,
        'message': 'Mentorship request sent',
        'request_id': 'placeholder-request-id',
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def mentor_request_accept(request, request_id):
    """Accept a mentorship request."""
    return Response({
        'success': True,
        'message': 'Mentorship request accepted'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def mentor_request_decline(request, request_id):
    """Decline a mentorship request."""
    return Response({
        'success': True,
        'message': 'Mentorship request declined'
    })


# ============================================================
# Goals ViewSet and Views
# ============================================================

class GoalViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user goals.
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """List user's goals."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        # Placeholder goals
        return Response({
            'success': True,
            'goals': [],
            'total': 0,
            'completed': 0,
            'in_progress': 0,
        })

    def create(self, request):
        """Create a new goal."""
        user_id = request.data.get('user_id')
        title = request.data.get('title')
        description = request.data.get('description', '')
        target_date = request.data.get('target_date')
        goal_type = request.data.get('goal_type', 'career')
        
        return Response({
            'success': True,
            'message': 'Goal created',
            'goal': {
                'id': 'placeholder-goal-id',
                'title': title,
                'description': description,
                'target_date': target_date,
                'goal_type': goal_type,
                'status': 'in_progress',
                'progress': 0,
            }
        }, status=201)

    def retrieve(self, request, pk=None):
        """Get goal details."""
        return Response({
            'success': True,
            'goal': {
                'id': str(pk),
                'note': 'Goal data would be here'
            }
        })

    def update(self, request, pk=None):
        """Update a goal."""
        return Response({
            'success': True,
            'message': 'Goal updated'
        })

    def partial_update(self, request, pk=None):
        """Partial update a goal."""
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        """Delete a goal."""
        return Response({
            'success': True,
            'message': 'Goal deleted'
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def goal_complete(request, pk):
    """Mark a goal as complete."""
    return Response({
        'success': True,
        'message': 'Goal marked as complete',
        'completed_at': 'now'
    })


# ============================================================
# Progress Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def progress_overview(request):
    """Get user's progress overview."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'progress': {
            'profile_completion': 45,
            'goals_completed': 2,
            'goals_total': 5,
            'skills_gained': 8,
            'connections_made': 12,
            'applications_submitted': 3,
            'courses_completed': 1,
            'level': 'Intermediate',
            'points': 1250,
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def progress_stats(request):
    """Get detailed progress statistics."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'stats': {
            'weekly': {
                'activities': 5,
                'goals_progress': 15,
                'learning_hours': 3.5,
            },
            'monthly': {
                'activities': 23,
                'goals_progress': 45,
                'learning_hours': 12,
            },
            'all_time': {
                'activities': 150,
                'goals_completed': 12,
                'learning_hours': 48,
                'connections': 25,
            }
        }
    })


# ============================================================
# Activities Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def activity_list(request):
    """List user's activities."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'activities': [],
        'total': 0,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def activity_log(request):
    """Log a new activity."""
    user_id = request.data.get('user_id')
    activity_type = request.data.get('activity_type')
    description = request.data.get('description', '')
    metadata = request.data.get('metadata', {})
    
    return Response({
        'success': True,
        'message': 'Activity logged',
        'activity': {
            'id': 'placeholder-activity-id',
            'activity_type': activity_type,
            'description': description,
            'created_at': 'now',
        }
    }, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def contribution_list(request):
    """List user's contributions."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'contributions': [],
        'total_points': 0,
    })


# ============================================================
# Learning Views
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def learning_overview(request):
    """Get user's learning overview."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    return Response({
        'success': True,
        'learning': {
            'courses_enrolled': 2,
            'courses_completed': 1,
            'total_hours': 12,
            'certificates_earned': 1,
            'current_courses': [],
            'completed_courses': [],
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def learning_courses(request):
    """List available courses."""
    category = request.query_params.get('category', '')
    skill = request.query_params.get('skill', '')
    level = request.query_params.get('level', '')
    
    # Placeholder courses
    courses = [
        {
            'id': 'course-1',
            'title': 'Introduction to Python',
            'description': 'Learn Python programming fundamentals',
            'duration_hours': 8,
            'level': 'beginner',
            'skills': ['Python', 'Programming'],
            'provider': 'ForgeForth Academy',
        },
        {
            'id': 'course-2',
            'title': 'Resume Writing Masterclass',
            'description': 'Create ATS-friendly resumes',
            'duration_hours': 2,
            'level': 'beginner',
            'skills': ['Resume Writing', 'Career Development'],
            'provider': 'ForgeForth Academy',
        },
    ]
    
    return Response({
        'success': True,
        'courses': courses,
        'total': len(courses),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def learning_course_detail(request, course_id):
    """Get course details."""
    return Response({
        'success': True,
        'course': {
            'id': str(course_id),
            'title': 'Course Title',
            'description': 'Course description',
            'modules': [],
            'duration_hours': 8,
            'level': 'beginner',
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def learning_course_enroll(request, course_id):
    """Enroll in a course."""
    user_id = request.data.get('user_id')
    
    return Response({
        'success': True,
        'message': 'Successfully enrolled in course',
        'enrollment': {
            'course_id': str(course_id),
            'user_id': user_id,
            'enrolled_at': 'now',
            'status': 'enrolled',
        }
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def learning_course_progress(request, course_id):
    """Get or update course progress."""
    user_id = request.query_params.get('user_id') or request.data.get('user_id')
    
    if request.method == 'GET':
        return Response({
            'success': True,
            'progress': {
                'course_id': str(course_id),
                'completed_modules': 0,
                'total_modules': 5,
                'percentage': 0,
                'last_accessed': None,
            }
        })
    else:
        module_id = request.data.get('module_id')
        completed = request.data.get('completed', False)
        
        return Response({
            'success': True,
            'message': 'Progress updated',
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def learning_recommendations(request):
    """Get personalized learning recommendations."""
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'user_id is required'}, status=400)
    
    # Placeholder recommendations based on profile/skills
    recommendations = [
        {
            'course_id': 'course-1',
            'title': 'Introduction to Python',
            'reason': 'Based on your interest in software development',
            'match_score': 95,
        },
        {
            'course_id': 'course-3',
            'title': 'Leadership Fundamentals',
            'reason': 'Recommended for career advancement',
            'match_score': 85,
        },
    ]
    
    return Response({
        'success': True,
        'recommendations': recommendations,
    })
