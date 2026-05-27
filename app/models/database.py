"""
Database models for Career Revolution.
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    documents = relationship("UserDocument", back_populates="user")
    skills = relationship("UserSkill", back_populates="user")
    experiences = relationship("UserExperience", back_populates="user")
    educations = relationship("UserEducation", back_populates="user")
    job_opportunities = relationship("JobOpportunity", back_populates="user")

class UserProfile(Base):
    """Extended user profile information."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    phone = Column(String(50))
    location = Column(String(255))
    linkedin_url = Column(String(500))
    github_url = Column(String(500))
    portfolio_url = Column(String(500))
    profile_picture_url = Column(String(1000))
    summary = Column(Text)
    current_job_title = Column(String(255))
    current_company = Column(String(255))
    desired_job_title = Column(String(255))
    desired_industry = Column(String(255))
    desired_location = Column(String(255))
    sector = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    salary_expectation = Column(String(100))
    notice_period = Column(String(50))
    
    # Personal Details for CV
    dob = Column(String(50))
    nationality = Column(String(100))
    marital_status = Column(String(100))
    work_auth = Column(String(100))
    
    # Refined Job Preferences
    job_types = Column(Text)  # JSON array: ["permanent", "contract"]
    work_modes = Column(Text) # JSON array: ["onsite", "hybrid", "remote"]
    experience_level = Column(String(100)) # e.g., "Mid-Senior Level"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="profile")

class UserDocument(Base):
    """User uploaded documents (CVs, certifications, etc.)."""
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_type = Column(String(50), nullable=False)  # 'resume', 'certification', 'portfolio', 'other'
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    processing_error = Column(Text)
    extracted_data = Column(Text)  # JSON string of extracted data
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")

class UserSkill(Base):
    """User skills extracted from documents."""
    __tablename__ = "user_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String(255), nullable=False)
    category = Column(String(100))  # 'technical', 'soft', 'language', 'certification'
    proficiency = Column(String(50))  # 'beginner', 'intermediate', 'advanced', 'expert'
    years_experience = Column(Integer)
    last_used = Column(Integer)  # Year last used
    source_document_id = Column(Integer, ForeignKey("user_documents.id"), nullable=True)
    confidence_score = Column(Integer)  # 0-100 confidence in extraction
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="skills")

class UserExperience(Base):
    """Work experience entries."""
    __tablename__ = "user_experience"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    location = Column(String(255))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # Null for current position
    is_current = Column(Boolean, default=False)
    description = Column(Text)
    achievements = Column(Text)
    skills_used = Column(Text)  # JSON array of skill names
    source_document_id = Column(Integer, ForeignKey("user_documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="experiences")

class UserEducation(Base):
    """Education history."""
    __tablename__ = "user_education"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), nullable=False)
    field_of_study = Column(String(255))
    location = Column(String(255))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_completed = Column(Boolean, default=True)
    grade = Column(String(50))
    achievements = Column(Text)
    source_document_id = Column(Integer, ForeignKey("user_documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="educations")

class VerificationToken(Base):
    """Email verification tokens."""
    __tablename__ = "verification_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    token_type = Column(String(50), default="email_verification")  # email_verification, password_reset
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")

class JobSource(Base):
    """Job sources (portals, company pages, boutique recruiters)."""
    __tablename__ = "job_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    source_type = Column(String(100))  # 'standard_portal', 'company_career_page', 'boutique_recruiter'
    industry_focus = Column(String(255))  # e.g., 'Pharma', 'Finance'
    location_focus = Column(String(255))  # e.g., 'Basel, Switzerland'
    country = Column(String(100), default='Switzerland')
    quality_score = Column(Integer, default=50)  # 0-100
    maturity_level = Column(String(50), default='new')  # 'new', 'qualified', 'expert', 'invalid'
    sector = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    tags = Column(Text, nullable=True)  # JSON array of tags
    last_checked = Column(DateTime, nullable=True)
    # Visual validation fields (set by Playwright + Gemini Vision during vetting)
    visual_validated = Column(Boolean, nullable=True)  # True=confirmed shows job listings, False=failed, None=not yet checked
    validation_notes = Column(Text, nullable=True)     # LLM reasoning from visual check
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    opportunities = relationship("JobOpportunity", back_populates="source")

class JobOpportunity(Base):
    """Real job opportunities fetched and validated."""
    __tablename__ = "job_opportunities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable if shared
    source_id = Column(Integer, ForeignKey("job_sources.id"), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    application_url = Column(String(1000), nullable=False)
    salary_range = Column(String(100))
    skills_required = Column(Text)  # JSON array
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_validated_at = Column(DateTime, default=datetime.utcnow)
    is_live = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    validation_notes = Column(Text)
    job_type = Column(String(50))     # 'Permanent', 'Contract'
    work_mode = Column(String(50))    # 'On-site', 'Hybrid', 'Remote'
    experience_level = Column(String(50)) # 'Entry', 'Mid-Snr', 'Executive'
    relevance_score = Column(Integer)  # 0-100
    
    # Relationships
    user = relationship("User", back_populates="job_opportunities")
    source = relationship("JobSource", back_populates="opportunities")

class JobApplication(Base):
    """Stores prepared application materials and status."""
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_opportunity_id = Column(Integer, ForeignKey("job_opportunities.id"), nullable=True) # Optional for manual entries
    application_url = Column(String(1000), nullable=True) # For manual entries
    status = Column(String(50), default='draft') # 'draft', 'prepared', 'applied', 'rejected', 'interviewing', 'offered'
    tailored_cv = Column(Text) 
    cover_letter = Column(Text)
    cv_path = Column(String(1000), nullable=True) # Path to generated PDF/Docx
    cl_path = Column(String(1000), nullable=True) # Path to generated PDF/Docx
    generated_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Auto-apply feedback loop columns
    intervention_message = Column(Text, nullable=True)
    auto_apply_log = Column(Text, nullable=True)  # JSON string
    auto_apply_intervention_data = Column(Text, nullable=True)  # JSON string for field-specific info
    
    # Relationships
    user = relationship("User")
    job_opportunity = relationship("JobOpportunity")

class JobMatch(Base):
    """User-specific matching scores for shared jobs."""
    __tablename__ = "job_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_opportunity_id = Column(Integer, ForeignKey("job_opportunities.id"), nullable=False)
    relevance_score = Column(Integer)
    is_verified = Column(Boolean, default=False)
    match_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    opportunity = relationship("JobOpportunity")


class AutoApplyCredential(Base):
    """
    Securely stores encrypted login credentials for job portals.
    Passwords are AES-encrypted using Fernet before saving.
    """
    __tablename__ = "auto_apply_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # LinkedIn
    linkedin_url = Column(String(500), nullable=True)
    linkedin_username = Column(String(255), nullable=True)
    linkedin_password_enc = Column(Text, nullable=True)  # Encrypted

    # Primary email used for job applications
    email_username = Column(String(255), nullable=True)
    email_password_enc = Column(Text, nullable=True)  # Encrypted

    # Any other platform-specific credentials stored as encrypted JSON string
    # e.g. '{"workday": {"username": "x", "password_enc": "..."}}'
    other_credentials_enc = Column(Text, nullable=True)

    # AI provider preference for this user: "gemini" | "claude"
    llm_provider = Column(String(20), default="gemini", nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")


class AutoApplyAccount(Base):
    """
    Tracks new accounts created by the automation during application processes.
    E.g., if a new Novartis/Workday account was registered, it's stored here
    so the user can see and access their new credentials.
    Passwords stored in plaintext here — this is the user's own visibility record.
    """
    __tablename__ = "auto_apply_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=True)

    platform_name = Column(String(255), nullable=False)   # e.g. "Novartis Careers (Workday)"
    platform_url = Column(String(500), nullable=True)
    username = Column(String(255), nullable=True)          # The account username/email used
    password = Column(String(255), nullable=True)          # Plaintext — user's own record
    notes = Column(Text, nullable=True)                    # e.g. "Account created during Easy Apply"

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    application = relationship("JobApplication")

# ─────────────────────────────────────────────────────────────────────────────
# Social Visibility
# ─────────────────────────────────────────────────────────────────────────────

class SocialTopicIdea(Base):
    """AI-suggested or user-provided topic ideas for social content."""
    __tablename__ = "social_topic_ideas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    # ai_suggested | user_provided
    source = Column(String(50), default="ai_suggested")
    # thought_leadership | how_to | case_study | career_story | industry_insight
    category = Column(String(100), nullable=True)
    relevance_score = Column(Integer, default=7)   # 1-10
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class SocialContentPiece(Base):
    """
    A single piece of AI-generated social content (article, post, etc.).
    Covers the full lifecycle: draft → approved → scheduled → published.
    """
    __tablename__ = "social_content_pieces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_idea_id = Column(Integer, ForeignKey("social_topic_ideas.id"), nullable=True)

    title = Column(String(500), nullable=False)
    # article | post | thread | headline_variant | about_section | comment_template
    content_type = Column(String(50), nullable=False)
    # linkedin | github | twitter | medium | portfolio
    platform = Column(String(50), default="linkedin")
    # draft | approved | scheduled | published
    status = Column(String(50), default="draft")

    body = Column(Text, nullable=True)             # Main content (markdown)
    hook_a = Column(Text, nullable=True)           # Opening hook variant A
    hook_b = Column(Text, nullable=True)           # Opening hook variant B
    hashtags = Column(Text, nullable=True)         # JSON list
    tags = Column(Text, nullable=True)             # JSON list (internal)
    word_count = Column(Integer, nullable=True)
    estimated_read_minutes = Column(Integer, nullable=True)
    ai_score = Column(Integer, nullable=True)      # 1-10 quality score from audit
    ai_feedback = Column(Text, nullable=True)      # Critic notes

    # Tone used for generation
    tone = Column(String(50), default="thought_leader")
    # The prompt context used (for regeneration traceability)
    generation_context = Column(Text, nullable=True)  # JSON

    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    published_url = Column(String(1000), nullable=True)
    engagement_notes = Column(Text, nullable=True)   # User's manual notes post-publish

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    topic_idea = relationship("SocialTopicIdea")


class UserSocialPlatformConfig(Base):
    """Which social platforms the user has enabled + automation status."""
    __tablename__ = "user_social_platform_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(50), nullable=False)       # linkedin | twitter | medium | github | portfolio | instagram | youtube | facebook
    enabled = Column(Boolean, default=False)
    automation_type = Column(String(50), default="none")  # none | browser | api
    platform_handle = Column(String(255), nullable=True)  # @username or profile handle
    platform_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Session & Jobs
# ─────────────────────────────────────────────────────────────────────────────

class LinkedInSession(Base):
    """
    Stores the user's LinkedIn browser session (encrypted cookies).
    One active row per user — reused across job fetches to avoid repeated login.
    """
    __tablename__ = "linkedin_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Encrypted Fernet blobs
    cookies_enc = Column(Text, nullable=True)        # JSON array of Playwright cookies
    linkedin_email_enc = Column(Text, nullable=True) # LinkedIn login email
    linkedin_pw_enc = Column(Text, nullable=True)    # LinkedIn login password

    is_valid = Column(Boolean, default=False)        # False until first successful login
    last_login_at = Column(DateTime, nullable=True)
    last_fetch_at = Column(DateTime, nullable=True)
    profile_name = Column(String(255), nullable=True)  # Confirmed name shown after login
    profile_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class LinkedInJob(Base):
    """
    Jobs fetched from LinkedIn using the user's authenticated session.
    Kept separate from the generic JobOpportunity pool so LinkedIn
    personalisation (Easy Apply, network overlap) is preserved.
    """
    __tablename__ = "linkedin_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    linkedin_job_id = Column(String(100), nullable=True, index=True)  # LinkedIn's own ID
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    job_url = Column(String(1000), nullable=False)
    description_snippet = Column(Text, nullable=True)

    # LinkedIn-specific signals
    easy_apply = Column(Boolean, default=False)
    network_overlap = Column(String(100), nullable=True)  # e.g. "3 connections work here"
    posted_at_text = Column(String(100), nullable=True)   # e.g. "2 days ago"

    # Scoring (set during align phase)
    relevance_score = Column(Integer, default=0)

    # Source: "jobs_for_you" | "search" | "saved"
    fetch_source = Column(String(50), default="jobs_for_you")

    first_seen_at = Column(DateTime, default=datetime.utcnow)
    is_live = Column(Boolean, default=True)

    user = relationship("User")


# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Profile Audit  (standalone feature — placement TBD)
# ─────────────────────────────────────────────────────────────────────────────

class LinkedInProfileAudit(Base):
    """
    Stores a point-in-time audit of the user's LinkedIn profile.
    Each run creates a new row; the latest row is the current state.
    """
    __tablename__ = "linkedin_profile_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audited_at = Column(DateTime, default=datetime.utcnow)

    profile_url = Column(String(500), nullable=True)
    raw_scraped_text = Column(Text, nullable=True)   # What was fetched from the profile page

    # Scores (0-100)
    completeness_score = Column(Integer, nullable=True)
    visibility_score = Column(Integer, nullable=True)
    keyword_score = Column(Integer, nullable=True)
    overall_score = Column(Integer, nullable=True)

    # Headline
    headline_current = Column(Text, nullable=True)
    headline_suggested = Column(Text, nullable=True)  # JSON list of 5 variants

    # About / Summary
    about_current = Column(Text, nullable=True)
    about_suggested = Column(Text, nullable=True)

    # Gaps and action items — JSON arrays
    gaps = Column(Text, nullable=True)              # [{section, issue, impact: high|medium|low}]
    action_items = Column(Text, nullable=True)      # [{action, impact, effort}]
    keywords_missing = Column(Text, nullable=True)  # JSON list
    keywords_present = Column(Text, nullable=True)  # JSON list

    # Full structured analysis from AI
    full_analysis = Column(Text, nullable=True)     # JSON

    user = relationship("User")


# Database engine and session
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./career_revolution.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database, create all tables."""
    Base.metadata.create_all(bind=engine)

# Auto-migration for missing columns (Self-healing - Runs on import)
if DATABASE_URL.startswith("sqlite"):
    try:
        import sqlite3
        import os
        # Extract filename and ensure absolute path
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        if not os.path.isabs(db_path):
            # Resolve relative to project root: database.py lives at app/models/database.py
            # so project root is three dirname() calls up
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, db_path)
            
        print(f"INFO: Database Auto-migration checking: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for col, col_type in [
            ("job_type", "VARCHAR(50)"),
            ("work_mode", "VARCHAR(50)"),
            ("experience_level", "VARCHAR(50)")
        ]:
            try:
                cursor.execute(f"ALTER TABLE job_opportunities ADD COLUMN {col} {col_type}")
                print(f"INFO: Added missing database column: {col}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # LLM provider preference on auto_apply_credentials
        for col, col_type in [
            ("llm_provider", "VARCHAR(20)"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE auto_apply_credentials ADD COLUMN {col} {col_type}")
                print(f"INFO: Added missing database column: auto_apply_credentials.{col}")
            except sqlite3.OperationalError:
                pass

        # Auto-apply feedback loop columns for job_applications
        for col, col_type in [
            ("intervention_message", "TEXT"),
            ("auto_apply_log", "TEXT"),
            ("auto_apply_intervention_data", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE job_applications ADD COLUMN {col} {col_type}")
                print(f"INFO: Added missing database column: job_applications.{col}")
            except sqlite3.OperationalError:
                pass  # Column already exists
        # Visual validation columns for job_sources
        for col, col_type in [
            ("visual_validated", "BOOLEAN"),
            ("validation_notes", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE job_sources ADD COLUMN {col} {col_type}")
                print(f"INFO: Added missing database column: job_sources.{col}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Create any missing tables via SQLAlchemy
        for tbl in ["user_social_platform_configs", "social_topic_ideas", "social_content_pieces",
                    "linkedin_profile_audits", "linkedin_sessions", "linkedin_jobs"]:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
            if not cursor.fetchone():
                conn.close()
                Base.metadata.create_all(bind=engine)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                print(f"INFO: Created missing table: {tbl}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"WARNING: Database Auto-migration error: {e}")

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()