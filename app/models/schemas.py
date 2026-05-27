"""
Pydantic schemas for Career Revolution API.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import json

# Enums
class DocumentType(str, Enum):
    RESUME = "resume"
    CERTIFICATION = "certification"
    PORTFOLIO = "portfolio"
    PROFILE_PICTURE = "profile_picture"
    OTHER = "other"

class SkillCategory(str, Enum):
    TECHNICAL = "technical"
    SOFT = "soft"
    LANGUAGE = "language"
    CERTIFICATION = "certification"

class ProficiencyLevel(str, Enum):
    BEGINNER = "beginner"
    LIMITED = "limited"
    INTERMEDIATE = "intermediate"
    PROFESSIONAL = "professional"
    ADVANCED = "advanced"
    FLUENT = "fluent"
    EXPERT = "expert"
    NATIVE = "native"

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Profile schemas
class ProfileBase(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    summary: Optional[str] = None
    current_job_title: Optional[str] = None
    current_company: Optional[str] = None
    desired_job_title: Optional[str] = None
    desired_industry: Optional[str] = None
    desired_location: Optional[str] = None
    salary_expectation: Optional[str] = None
    notice_period: Optional[str] = None
    
    # Personal Details for CV
    dob: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    work_auth: Optional[str] = None
    
    job_types: Optional[List[str]] = None
    work_modes: Optional[List[str]] = None
    experience_level: Optional[str] = None

class ProfileResponse(ProfileBase):
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

    @validator('job_types', 'work_modes', pre=True)
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        return v
    # Ensure nested serialization for DB objects
    @validator('job_types', 'work_modes')
    def ensure_list(cls, v):
        return v or []

# Document schemas
class DocumentBase(BaseModel):
    document_type: DocumentType
    original_filename: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    stored_filename: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_processed: bool
    processing_status: str
    processing_error: Optional[str] = None
    extracted_data: Optional[str] = None
    upload_date: datetime
    processed_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Skill schemas
class SkillBase(BaseModel):
    skill_name: str
    category: Optional[SkillCategory] = None
    proficiency: Optional[ProficiencyLevel] = None
    years_experience: Optional[int] = None
    last_used: Optional[int] = None

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int
    user_id: int
    source_document_id: Optional[int] = None
    confidence_score: Optional[int] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Experience schemas
class ExperienceBase(BaseModel):
    company: str
    position: str
    location: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    is_current: bool = False
    description: Optional[str] = None
    achievements: Optional[str] = None
    skills_used: Optional[List[str]] = None

class ExperienceCreate(ExperienceBase):
    pass

class ExperienceUpdate(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None
    achievements: Optional[str] = None
    skills_used: Optional[List[str]] = None

class ExperienceResponse(ExperienceBase):
    id: int
    user_id: int
    source_document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Education schemas
class EducationBase(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_completed: bool = True
    grade: Optional[str] = None
    achievements: Optional[str] = None

class EducationCreate(EducationBase):
    pass

class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_completed: Optional[bool] = None
    grade: Optional[str] = None
    achievements: Optional[str] = None

class EducationResponse(EducationBase):
    id: int
    user_id: int
    source_document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Dashboard response
class UserDashboard(BaseModel):
    user: UserResponse
    profile: Optional[ProfileResponse] = None
    documents: List[DocumentResponse] = []
    skills: List[SkillResponse] = []
    experiences: List[ExperienceResponse] = []
    educations: List[EducationResponse] = []
    stats: dict = {
        "total_documents": 0,
        "processed_documents": 0,
        "total_skills": 0,
        "total_experience": 0,
        "profile_completion": 0
    }

# LinkedIn schemas
class LinkedInExtractionResult(BaseModel):
    success: bool
    document_id: int
    user_id: int
    original_filename: str
    linkedin_urls_found: List[str] = []
    url_count: int = 0
    text_preview: Optional[str] = None
    profile_updated: bool = False
    error: Optional[str] = None

class LinkedInAnalysisOptions(BaseModel):
    analysis_type: str = "comprehensive"
    include_recommendations: bool = True
    include_templates: bool = False
    generate_plan: bool = True

class LinkedInAnalysisResult(BaseModel):
    success: bool
    linkedin_url: str
    analysis_type: str
    score: Optional[int] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    optimization_plan: Optional[str] = None
    generated_templates: List[str] = []
    report_path: Optional[str] = None
    error: Optional[str] = None

class LinkedInStatus(BaseModel):
    user_id: int
    linkedin_url: Optional[str] = None
    linkedin_status: str  # not_found, found, verified, analyzed
    documents_total: int = 0
    documents_processed: int = 0
    linkedin_urls_found: List[str] = []
    profile_exists: bool = False
    profile_updated: Optional[datetime] = None

class LinkedInURLUpdate(BaseModel):
    linkedin_url: str
    @validator('linkedin_url')
    def validate_linkedin_url(cls, v):
        if not v or 'linkedin.com' not in v:
            raise ValueError('Invalid LinkedIn URL')
        return v

# Job Source schemas
class JobSourceBase(BaseModel):
    name: str
    url: str
    source_type: str = "general"
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    industry_focus: Optional[str] = None
    location_focus: Optional[str] = None
    country: str = "Switzerland"
    quality_score: int = 50
    maturity_level: str = "new"
    is_active: bool = True
    tags: Optional[List[str]] = None

class JobSourceCreate(JobSourceBase):
    pass

class JobSourceResponse(JobSourceBase):
    id: int
    last_checked: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    visual_validated: Optional[bool] = None
    validation_notes: Optional[str] = None
    class Config:
        from_attributes = True
    
    @validator('tags', pre=True)
    def parse_tags(cls, v):
        if v is None: return []
        if isinstance(v, str):
            try:
                import json
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except:
                return [t.strip() for t in v.split(',') if t.strip()]
        return v if isinstance(v, list) else [str(v)]

# Job Opportunity schemas
class JobOpportunityResponse(BaseModel):
    id: int
    source_id: int
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    application_url: str
    job_type: Optional[str] = None
    work_mode: Optional[str] = None
    experience_level: Optional[str] = None
    relevance_score: Optional[int] = None
    is_live: bool = True
    is_verified: bool = False
    first_seen_at: datetime
    
    class Config:
        from_attributes = True

# Job Match schemas
class JobMatchResponse(BaseModel):
    id: int
    user_id: int
    job_opportunity_id: int
    relevance_score: int
    is_verified: bool = False
    match_notes: Optional[str] = None
    created_at: datetime
    
    # Optional nested data
    job: Optional[JobOpportunityResponse] = None
    
    class Config:
        from_attributes = True

# Job Application schemas
class JobApplicationBase(BaseModel):
    job_opportunity_id: Optional[int] = None
    application_url: Optional[str] = None
    status: str = "draft"
    notes: Optional[str] = None

class JobApplicationCreate(JobApplicationBase):
    job_title: Optional[str] = None    # pre-populated from LinkedIn / external source
    company_name: Optional[str] = None

class JobApplicationResponse(JobApplicationBase):
    id: int
    user_id: int
    tailored_cv: Optional[str] = None
    cover_letter: Optional[str] = None
    cv_path: Optional[str] = None
    cl_path: Optional[str] = None
    generated_at: datetime
    applied_at: Optional[datetime] = None
    
    # Metadata for UI
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    job_description: Optional[str] = None
    
    # Auto-apply feedback loop fields
    intervention_message: Optional[str] = None
    auto_apply_log: Optional[str] = None
    auto_apply_intervention_data: Optional[str] = None
    
    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────
# Auto-Apply Settings & Account Schemas
# ─────────────────────────────────────────────────────────

class AutoApplySettingsRequest(BaseModel):
    """Payload to save/update auto-apply credentials."""
    linkedin_url: Optional[str] = None
    linkedin_username: Optional[str] = None
    linkedin_password: Optional[str] = None          # Plaintext on input, encrypted before save

    email_username: Optional[str] = None
    email_password: Optional[str] = None             # Plaintext on input, encrypted before save

    llm_provider: Optional[str] = None               # "gemini" | "claude"


class AutoApplySettingsResponse(BaseModel):
    """Response: usernames shown in plain, passwords masked."""
    configured: bool = False
    linkedin_url: Optional[str] = None
    linkedin_username: Optional[str] = None
    linkedin_password_set: bool = False              # True if a password is stored

    email_username: Optional[str] = None
    email_password_set: bool = False                 # True if a password is stored

    llm_provider: str = "gemini"                     # Active AI provider for this user


class AutoApplyAccountCreate(BaseModel):
    """Manually log a portal account created during automation."""
    platform_name: str
    platform_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    notes: Optional[str] = None
    application_id: Optional[int] = None


class AutoApplyAccountResponse(AutoApplyAccountCreate):
    """Response for portal accounts."""
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InterventionRequest(BaseModel):
    """User provides data to resume a stuck auto-apply."""
    action: str = "resume"                           # "resume" | "skip" | "abort"
    intervention_data: Optional[str] = None          # e.g. CAPTCHA solution, 2FA code, form field answers


# ─────────────────────────────────────────────────────────
# Multi-Agent CV/CL Execution Schemas
# ─────────────────────────────────────────────────────────

class BattlePlan(BaseModel):
    """Distilled job requirements and strategy from Analyzer Agent."""
    top_skills: List[str] = Field(..., description="Top 5 'Must-Have' skills for this job")
    company_voice: str = Field(..., description="The detected company voice (e.g. Corporate, Startup, Academic)")
    keywords: List[str] = Field(default_factory=list, description="Top 10-15 keywords from the job description for ATS optimization")
    highlight_achievements: List[str] = Field(..., description="3 specific achievements from the user's history that must be highlighted")

class AuditReport(BaseModel):
    """Quality score and feedback from Critic Agent."""
    score: int = Field(..., ge=0, le=10, description="Quality score (1-10)")
    feedback: str = Field(..., description="Specific feedback on how to improve the CV/CL")
    is_approved: bool = Field(..., description="True if score >= 8 and no hallucinations found")
    hallucination_check: bool = Field(default=True, description="False if claims not found in USER DATA were identified")
    keyword_saturation: int = Field(default=0, description="Percentage (0-100) of target keywords found in the content")