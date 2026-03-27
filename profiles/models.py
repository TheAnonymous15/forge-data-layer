# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Profile Models
=============================================
Talent profile models with skills, education, experience, etc.
"""
import uuid
from django.db import models
from django.conf import settings


class TalentProfile(models.Model):
    """Extended profile for talent users."""

    class AvailabilityStatus(models.TextChoices):
        ACTIVELY_LOOKING = 'actively_looking', 'Actively Looking'
        OPEN_TO_OFFERS = 'open_to_offers', 'Open to Offers'
        NOT_LOOKING = 'not_looking', 'Not Looking'

    class ExperienceLevel(models.TextChoices):
        ENTRY = 'entry', 'Entry Level (0-2 years)'
        JUNIOR = 'junior', 'Junior (2-4 years)'
        MID = 'mid', 'Mid-Level (4-7 years)'
        SENIOR = 'senior', 'Senior (7-10 years)'
        LEAD = 'lead', 'Lead/Principal (10+ years)'
        EXECUTIVE = 'executive', 'Executive'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='talent_profile'
    )

    # Professional Info
    headline = models.CharField(max_length=200, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        null=True,
        blank=True
    )

    # Availability
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.OPEN_TO_OFFERS
    )
    available_from = models.DateField(null=True, blank=True)

    # Preferences
    preferred_job_types = models.JSONField(default=list, blank=True)  # ['full_time', 'contract', etc.]
    preferred_locations = models.JSONField(default=list, blank=True)
    remote_preference = models.CharField(max_length=20, null=True, blank=True)  # onsite, remote, hybrid
    salary_expectation_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_expectation_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='ZAR')

    # Links
    linkedin_url = models.URLField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    portfolio_url = models.URLField(null=True, blank=True)
    website_url = models.URLField(null=True, blank=True)

    # Profile completeness
    profile_completeness = models.IntegerField(default=0)  # 0-100%
    profile_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Privacy
    is_public = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'talent_profiles'
        verbose_name = 'Talent Profile'
        verbose_name_plural = 'Talent Profiles'

    def __str__(self):
        return f"Profile: {self.user.email}"


class Skill(models.Model):
    """Skills taxonomy."""

    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Technical'
        SOFT = 'soft', 'Soft Skills'
        LANGUAGE = 'language', 'Language'
        TOOL = 'tool', 'Tool/Software'
        INDUSTRY = 'industry', 'Industry Knowledge'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TECHNICAL)
    description = models.TextField(null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_verified = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'skills'
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'
        ordering = ['name']

    def __str__(self):
        return self.name


class TalentSkill(models.Model):
    """Association between talent profiles and skills."""

    class ProficiencyLevel(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='talent_skills')
    proficiency = models.CharField(max_length=20, choices=ProficiencyLevel.choices, default=ProficiencyLevel.INTERMEDIATE)
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    endorsements_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'talent_skills'
        unique_together = ['profile', 'skill']
        ordering = ['-is_primary', '-proficiency', '-years_of_experience']

    def __str__(self):
        return f"{self.profile.user.email} - {self.skill.name}"


class Education(models.Model):
    """Educational background."""

    class DegreeType(models.TextChoices):
        HIGH_SCHOOL = 'high_school', 'High School'
        CERTIFICATE = 'certificate', 'Certificate'
        DIPLOMA = 'diploma', 'Diploma'
        ASSOCIATE = 'associate', 'Associate Degree'
        BACHELOR = 'bachelor', 'Bachelor\'s Degree'
        MASTER = 'master', 'Master\'s Degree'
        DOCTORATE = 'doctorate', 'Doctorate'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name='education')
    institution = models.CharField(max_length=200)
    degree_type = models.CharField(max_length=20, choices=DegreeType.choices)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    grade = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'education'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.profile.user.email} - {self.institution}"


class WorkExperience(models.Model):
    """Work experience history."""

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'
        CONTRACT = 'contract', 'Contract'
        FREELANCE = 'freelance', 'Freelance'
        INTERNSHIP = 'internship', 'Internship'
        VOLUNTEER = 'volunteer', 'Volunteer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name='work_experience')
    company = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    location = models.CharField(max_length=200, null=True, blank=True)
    is_remote = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    achievements = models.JSONField(default=list, blank=True)
    skills_used = models.ManyToManyField(Skill, blank=True, related_name='work_experiences')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'work_experience'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.profile.user.email} - {self.title} at {self.company}"


class Certification(models.Model):
    """Professional certifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    credential_id = models.CharField(max_length=100, null=True, blank=True)
    credential_url = models.URLField(null=True, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    does_not_expire = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name='certifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certifications'
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.profile.user.email} - {self.name}"


class Language(models.Model):
    """Language proficiency."""

    class ProficiencyLevel(models.TextChoices):
        ELEMENTARY = 'elementary', 'Elementary'
        LIMITED_WORKING = 'limited_working', 'Limited Working'
        PROFESSIONAL_WORKING = 'professional_working', 'Professional Working'
        FULL_PROFESSIONAL = 'full_professional', 'Full Professional'
        NATIVE = 'native', 'Native/Bilingual'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name='languages')
    language = models.CharField(max_length=50)
    proficiency = models.CharField(max_length=30, choices=ProficiencyLevel.choices)
    is_native = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'languages'
        unique_together = ['profile', 'language']

    def __str__(self):
        return f"{self.profile.user.email} - {self.language}"

