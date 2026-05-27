"""
Shared fixtures for Career Revolution test suite.

Provides:
  - in-memory SQLite session (no real DB touched)
  - pre-built User + UserProfile + skills + experiences
  - auth token for that user
  - FastAPI TestClient with DB and current-user overrides
  - mock factories for LLM, PDF, LinkedIn browser, ExtractionService
"""

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── Path setup so tests run from repo root ───────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load .env so CREDENTIAL_ENCRYPTION_KEY and other secrets are available to all tests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Patch the Windows event-loop policy override before importing main.py
# (the override freezes the policy; that breaks pytest-asyncio's own loop management)
import asyncio
asyncio.set_event_loop_policy = lambda p: None  # neutralise the freeze

from app.models.database import (
    Base, User, UserProfile, UserSkill, UserExperience, UserEducation,
    JobSource, JobOpportunity, JobApplication, LinkedInSession, LinkedInJob,
)
from app.services.auth import get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# ── In-memory DB ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory SQLite session per test."""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ── Seeded user with full profile ────────────────────────────────────────────

@pytest.fixture
def test_user(db):
    """User + UserProfile + skills + experience already in DB."""
    user = User(
        email="testuser@example.com",
        password_hash=get_password_hash("password123"),
        full_name="Alex Mueller",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        phone="+41 79 123 45 67",
        location="Zurich, Switzerland",
        summary="Senior IT Director with 15 years in digital transformation.",
        dob="1980-06-01",
        nationality="Swiss",
        marital_status="Married",
        work_auth="EU/Swiss Citizen",
        linkedin_url="https://linkedin.com/in/alexmueller",
        updated_at=datetime.utcnow() - timedelta(days=5),
    )
    db.add(profile)

    # Technical skills
    for skill in ["Python", "Cloud Architecture", "Agile", "SAP"]:
        db.add(UserSkill(user_id=user.id, skill_name=skill, category="technical"))

    # Soft skills
    for skill in ["Leadership", "Communication", "Strategic Thinking"]:
        db.add(UserSkill(user_id=user.id, skill_name=skill, category="soft"))

    # Language
    db.add(UserSkill(user_id=user.id, skill_name="German", category="language", proficiency="native"))
    db.add(UserSkill(user_id=user.id, skill_name="English", category="language", proficiency="fluent"))

    # Experience
    db.add(UserExperience(
        user_id=user.id,
        position="IT Director",
        company="Acme AG",
        start_date=datetime(2018, 1, 1),
        end_date=None,
        description="Led digital transformation.\nReduced costs by 30%.\nManaged 40-person team.",
    ))
    db.add(UserExperience(
        user_id=user.id,
        position="Senior IT Manager",
        company="Beta GmbH",
        start_date=datetime(2014, 3, 1),
        end_date=datetime(2017, 12, 31),
        description="Cloud migration for 5 subsidiaries.\nAgile adoption.",
    ))

    # Education
    db.add(UserEducation(
        user_id=user.id,
        institution="ETH Zurich",
        degree="MSc Computer Science",
        end_date=datetime(2006, 6, 1),
    ))

    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Valid JWT for test_user."""
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── LinkedIn session helpers ─────────────────────────────────────────────────

@pytest.fixture
def linkedin_session(db, test_user):
    """A fresh, valid LinkedIn session for test_user."""
    from app.utils.security import encrypt_value
    row = LinkedInSession(
        user_id=test_user.id,
        linkedin_email_enc=encrypt_value("li@example.com"),
        linkedin_pw_enc=encrypt_value("lipassword"),
        cookies_enc=encrypt_value(json.dumps([{"name": "li_at", "value": "TOKEN", "domain": ".linkedin.com"}])),
        is_valid=True,
        last_login_at=datetime.utcnow() - timedelta(hours=1),
        last_fetch_at=None,
        profile_name="Alex Mueller",
    )
    db.add(row)
    db.commit()
    return row


@pytest.fixture
def stale_linkedin_session(db, test_user):
    """A LinkedIn session that has expired (> 25 days old)."""
    from app.utils.security import encrypt_value
    row = LinkedInSession(
        user_id=test_user.id,
        linkedin_email_enc=encrypt_value("li@example.com"),
        linkedin_pw_enc=encrypt_value("lipassword"),
        cookies_enc=encrypt_value(json.dumps([{"name": "li_at", "value": "OLD_TOKEN", "domain": ".linkedin.com"}])),
        is_valid=True,
        last_login_at=datetime.utcnow() - timedelta(days=30),
        last_fetch_at=None,
        profile_name="Alex Mueller",
    )
    db.add(row)
    db.commit()
    return row


# ── Job / Application helpers ────────────────────────────────────────────────

@pytest.fixture
def job_source(db):
    src = JobSource(
        name="LinkedIn",
        url="https://www.linkedin.com/jobs/",
        source_type="standard_portal",
        country="Switzerland",
        is_active=True,
    )
    db.add(src)
    db.commit()
    return src


@pytest.fixture
def job_opportunity(db, job_source):
    """A JobOpportunity with a full description (no scraping needed)."""
    opp = JobOpportunity(
        source_id=job_source.id,
        title="Head of IT",
        company="MegaCorp AG",
        location="Zurich",
        application_url="https://www.linkedin.com/jobs/view/99999/",
        description=(
            "We are looking for a Head of IT to lead our digital transformation. "
            "Requirements: 10+ years IT leadership, cloud architecture, agile methodologies, "
            "SAP S/4HANA, stakeholder management. Budget responsibility: CHF 10M. "
            "Team of 50 engineers. Reports to CTO. Must have Swiss work authorisation."
        ),
        is_live=True,
    )
    db.add(opp)
    db.commit()
    return opp


@pytest.fixture
def job_opportunity_no_desc(db, job_source):
    """A JobOpportunity with NO description — requires scraping."""
    opp = JobOpportunity(
        source_id=job_source.id,
        title="CTO",
        company="StartupXYZ",
        location="Basel",
        application_url="https://www.linkedin.com/jobs/view/11111/",
        description=None,
        is_live=True,
    )
    db.add(opp)
    db.commit()
    return opp


@pytest.fixture
def draft_application(db, test_user, job_opportunity):
    """A JobApplication in draft state linked to a job with description."""
    app = JobApplication(
        user_id=test_user.id,
        job_opportunity_id=job_opportunity.id,
        application_url=job_opportunity.application_url,
        status="draft",
    )
    db.add(app)
    db.commit()
    return app


@pytest.fixture
def draft_application_no_desc(db, test_user, job_opportunity_no_desc):
    """A JobApplication linked to a job with no description."""
    app = JobApplication(
        user_id=test_user.id,
        job_opportunity_id=job_opportunity_no_desc.id,
        application_url=job_opportunity_no_desc.application_url,
        status="draft",
    )
    db.add(app)
    db.commit()
    return app


@pytest.fixture
def prepared_application(db, test_user, job_opportunity):
    """An application that already has tailored CV and cover letter."""
    app = JobApplication(
        user_id=test_user.id,
        job_opportunity_id=job_opportunity.id,
        application_url=job_opportunity.application_url,
        status="prepared",
        tailored_cv="# Alex Mueller\nIT Director\n\n## EXPERTISE\nLeading IT transformations...",
        cover_letter="Dear Hiring Manager,\n\nI am a perfect fit.\n\n- Reduced costs by 30%\n\nBest,\nAlex",
        cv_path="uploads/1/applications/1/CV.pdf",
        cl_path="uploads/1/applications/1/CL.pdf",
        generated_at=datetime.utcnow() - timedelta(hours=2),
    )
    db.add(app)
    db.commit()
    return app


# ── LLM mock factory ─────────────────────────────────────────────────────────

MOCK_BATTLE_PLAN = {
    "top_skills": ["Cloud Architecture", "IT Leadership", "SAP", "Agile", "Stakeholder Management"],
    "company_voice": "Blue Chip Corporate",
    "keywords": ["digital transformation", "cloud", "SAP S/4HANA", "agile", "IT strategy"],
    "highlight_achievements": ["cost reduction", "team leadership", "cloud migration"],
}

MOCK_TAILORED_CONTENT = {
    "tagline": "IT Director | Digital Transformation Leader",
    "expertise_summary": "Strategic IT Director with 15 years driving digital transformation and cloud migrations.",
    "tailored_experiences": [
        {
            "role": "IT Director",
            "company": "Acme AG",
            "dates": "2018 - Present",
            "bullets": [
                "Led digital transformation programme reducing operational costs by 30%.",
                "Managed cloud migration for 5 business units using agile methodology.",
            ],
        }
    ],
    "tailored_strengths": ["Leadership", "Cloud Architecture", "Strategic Thinking",
                           "Agile", "SAP S/4HANA", "Stakeholder Management",
                           "Budget Management", "Team Building", "Communication",
                           "Problem Solving"],
    "cover_letter": (
        "Dear Hiring Manager,\n\n"
        "I am an experienced IT Director with 15 years leading digital transformation.\n\n"
        "- Reduced costs by 30% through cloud migration at Acme AG\n"
        "- Led 40-person engineering teams across 5 subsidiaries\n"
        "- Delivered SAP S/4HANA rollout on time and under budget\n\n"
        "I am excited by MegaCorp AG's transformation agenda and would welcome an interview.\n\n"
        "Best regards,\nAlex Mueller"
    ),
}

MOCK_AUDIT_APPROVED = {
    "score": 9,
    "feedback": "Excellent alignment with job requirements.",
    "is_approved": True,
    "hallucination_check": [],
    "keyword_saturation": "85%",
}

MOCK_AUDIT_REJECTED = {
    "score": 6,
    "feedback": "Cover letter needs stronger bullet points demonstrating quantifiable achievements.",
    "is_approved": False,
    "hallucination_check": [],
    "keyword_saturation": "60%",
}

MOCK_AUDIT_HALLUCINATION = {
    "score": 7,
    "feedback": "Claims about AWS certification not found in user data.",
    "is_approved": False,
    "hallucination_check": ["AWS Certified Solutions Architect (not in user data)"],
    "keyword_saturation": "70%",
}


def make_mock_llm(battle_plan=None, content=None, audit=None):
    """Return an LLMAnalysisService mock with configurable responses."""
    mock = AsyncMock()
    responses = [
        battle_plan or MOCK_BATTLE_PLAN,
        content or MOCK_TAILORED_CONTENT,
        audit or MOCK_AUDIT_APPROVED,
    ]
    mock.generate_json = AsyncMock(side_effect=responses + [MOCK_TAILORED_CONTENT] * 10)
    return mock


# ── PDF service mock ─────────────────────────────────────────────────────────

def make_mock_pdf():
    mock = AsyncMock()
    mock.create_cv_pdf = AsyncMock(return_value=True)
    mock.create_cl_pdf = AsyncMock(return_value=True)
    return mock


# ── FastAPI TestClient fixture ────────────────────────────────────────────────

@pytest.fixture
def client(db, test_user, auth_token):
    """
    TestClient with:
      - DB overridden to in-memory session
      - current_user overridden to test_user
      - LLM + PDF services mocked so no real API calls are made
    """
    # Import app after path is set up
    import app.main as main_module

    def override_get_db():
        try:
            yield db
        finally:
            pass

    async def override_get_current_user():
        return test_user

    main_module.app.dependency_overrides[main_module.get_db] = override_get_db
    main_module.app.dependency_overrides[main_module.get_current_user] = override_get_current_user

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        c.headers.update({"Authorization": f"Bearer {auth_token}"})
        yield c

    main_module.app.dependency_overrides.clear()
