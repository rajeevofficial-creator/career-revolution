"""
Career Revolution — Full End-to-End Workflow Test Suite
========================================================

Covers every step from LinkedIn session setup through job confirmation:

  Module 1  — LinkedIn Connection & Session Management         (TC-LI-*)
  Module 2  — Job Fetching from LinkedIn                       (TC-FETCH-*)
  Module 3  — Application Creation                             (TC-APP-*)
  Module 4  — Job Description Fetching (prepare entry point)   (TC-DESC-*)
  Module 5  — Prepare Pipeline — LLM Phases                    (TC-PREP-*)
  Module 6  — PDF Generation                                   (TC-PDF-*)
  Module 7  — Full Prepare Integration (API level)             (TC-INT-*)
  Module 8  — Auto-Apply Engine                                (TC-AUTO-*)
  Module 9  — ExtractionService Unit Tests                     (TC-EXT-*)
  Module 10 — LLM Bridge Unit Tests                            (TC-LLM-*)

Run with:
  pytest tests/test_workflow_linkedin_to_apply.py -v
"""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.models.database import (
    JobApplication, JobOpportunity, LinkedInSession, LinkedInJob,
    User, UserProfile,
)
from tests.conftest import (
    MOCK_AUDIT_APPROVED, MOCK_AUDIT_HALLUCINATION, MOCK_AUDIT_REJECTED,
    MOCK_BATTLE_PLAN, MOCK_TAILORED_CONTENT,
    make_mock_llm, make_mock_pdf,
)


# ─────────────────────────────────────────────────────────────────────────────
# Module 1: LinkedIn Connection & Session Management
# ─────────────────────────────────────────────────────────────────────────────

class TestLinkedInConnection:
    """TC-LI-* : Credential storage, login, session lifecycle."""

    def test_tc_li_01_save_credentials(self, db, test_user):
        """TC-LI-01 Saving credentials stores encrypted values and marks session invalid."""
        from app.services.linkedin_browser import LinkedInBrowserService
        svc = LinkedInBrowserService()
        svc.save_credentials(db, test_user.id, "user@linkedin.com", "secret")
        row = db.query(LinkedInSession).filter_by(user_id=test_user.id).first()
        assert row is not None
        assert row.is_valid is False
        assert row.linkedin_email_enc != "user@linkedin.com"   # must be encrypted

    def test_tc_li_02_session_status_not_connected(self, db, test_user):
        """TC-LI-02 No session row → connected=False."""
        from app.services.linkedin_browser import LinkedInBrowserService
        status = LinkedInBrowserService().session_status(db, test_user.id)
        assert status["connected"] is False
        assert status["has_credentials"] is False

    def test_tc_li_03_session_status_connected_fresh(self, db, test_user, linkedin_session):
        """TC-LI-03 Valid session logged in < 25 days ago → connected=True."""
        from app.services.linkedin_browser import LinkedInBrowserService
        status = LinkedInBrowserService().session_status(db, test_user.id)
        assert status["connected"] is True
        assert status["stale"] is False
        assert status["profile_name"] == "Alex Mueller"

    def test_tc_li_04_session_status_stale(self, db, test_user, stale_linkedin_session):
        """TC-LI-04 Session last login > 25 days ago → connected=False, stale=True."""
        from app.services.linkedin_browser import LinkedInBrowserService
        status = LinkedInBrowserService().session_status(db, test_user.id)
        assert status["connected"] is False
        assert status["stale"] is True
        assert status["has_credentials"] is True

    def test_tc_li_05_session_status_invalid_row(self, db, test_user):
        """TC-LI-05 Row exists but is_valid=False → connected=False."""
        from app.utils.security import encrypt_value
        row = LinkedInSession(
            user_id=test_user.id,
            linkedin_email_enc=encrypt_value("x@x.com"),
            linkedin_pw_enc=encrypt_value("pw"),
            is_valid=False,
        )
        db.add(row)
        db.commit()
        from app.services.linkedin_browser import LinkedInBrowserService
        status = LinkedInBrowserService().session_status(db, test_user.id)
        assert status["connected"] is False
        assert status["has_credentials"] is True

    def test_tc_li_06_disconnect_clears_session(self, db, test_user, linkedin_session):
        """TC-LI-06 Disconnect nullifies cookies and marks invalid."""
        from app.services.linkedin_browser import LinkedInBrowserService
        LinkedInBrowserService().disconnect(db, test_user.id)
        row = db.query(LinkedInSession).filter_by(user_id=test_user.id).first()
        assert row.is_valid is False
        assert row.cookies_enc is None
        assert row.profile_name is None

    @pytest.mark.asyncio
    async def test_tc_li_07_login_no_credentials(self, db, test_user):
        """TC-LI-07 Login without saved credentials returns (False, msg)."""
        from app.services.linkedin_browser import LinkedInBrowserService
        ok, msg = await LinkedInBrowserService().login(db, test_user.id)
        assert ok is False
        assert "No credentials" in msg

    def test_tc_li_08_save_credentials_overwrites_existing(self, db, test_user, linkedin_session):
        """TC-LI-08 Saving new credentials resets is_valid to False."""
        from app.services.linkedin_browser import LinkedInBrowserService
        LinkedInBrowserService().save_credentials(db, test_user.id, "new@linkedin.com", "newpw")
        row = db.query(LinkedInSession).filter_by(user_id=test_user.id).first()
        assert row.is_valid is False


# ─────────────────────────────────────────────────────────────────────────────
# Module 2: Job Fetching
# ─────────────────────────────────────────────────────────────────────────────

class TestJobFetching:
    """TC-FETCH-* : fetch_jobs happy path, throttle, dedup, stale-session re-login."""

    @pytest.mark.asyncio
    async def test_tc_fetch_01_not_connected_returns_error(self, db, test_user):
        """TC-FETCH-01 fetch_jobs with no session → failure message."""
        from app.services.linkedin_browser import LinkedInBrowserService
        ok, msg, count = await LinkedInBrowserService().fetch_jobs(db, test_user.id)
        assert ok is False
        assert count == 0
        assert "connect" in msg.lower()

    @pytest.mark.asyncio
    async def test_tc_fetch_02_throttle_within_30_min(self, db, test_user, linkedin_session):
        """TC-FETCH-02 Second fetch within 30-min window is rejected."""
        linkedin_session.last_fetch_at = datetime.utcnow() - timedelta(minutes=10)
        db.commit()
        from app.services.linkedin_browser import LinkedInBrowserService
        ok, msg, count = await LinkedInBrowserService().fetch_jobs(db, test_user.id)
        assert ok is False
        assert "wait" in msg.lower()

    @pytest.mark.asyncio
    async def test_tc_fetch_03_happy_path_saves_jobs(self, db, test_user, linkedin_session):
        """TC-FETCH-03 Successful fetch saves new LinkedInJob rows."""
        mock_jobs = [
            {"linkedin_job_id": "1001", "title": "IT Director", "company": "AlphaCorp",
             "location": "Zurich", "job_url": "https://www.linkedin.com/jobs/view/1001/",
             "easy_apply": True, "posted_at_text": "2d ago", "network_overlap": ""},
            {"linkedin_job_id": "1002", "title": "CTO", "company": "BetaAG",
             "location": "Basel", "job_url": "https://www.linkedin.com/jobs/view/1002/",
             "easy_apply": False, "posted_at_text": "5d ago", "network_overlap": ""},
        ]
        from app.services.linkedin_browser import LinkedInBrowserService
        svc = LinkedInBrowserService()
        with patch.object(svc, "_scrape_jobs_for_you", new=AsyncMock(return_value=mock_jobs)), \
             patch("playwright.async_api.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=_fake_playwright())
            ok, msg, count = await svc.fetch_jobs(db, test_user.id, fetch_source="jobs_for_you")

        assert ok is True
        assert count == 2
        stored = db.query(LinkedInJob).filter_by(user_id=test_user.id).all()
        assert len(stored) == 2
        assert any(j.linkedin_job_id == "1001" for j in stored)

    @pytest.mark.asyncio
    async def test_tc_fetch_04_duplicate_jobs_not_doubled(self, db, test_user, linkedin_session):
        """TC-FETCH-04 Fetching the same job twice only stores it once."""
        mock_jobs = [
            {"linkedin_job_id": "2001", "title": "VP IT", "company": "Gamma",
             "location": "Geneva", "job_url": "https://www.linkedin.com/jobs/view/2001/",
             "easy_apply": False, "posted_at_text": "", "network_overlap": ""},
        ]
        # Pre-seed an existing LinkedInJob with the same linkedin_job_id
        db.add(LinkedInJob(
            user_id=test_user.id, linkedin_job_id="2001",
            title="VP IT", company="Gamma",
            job_url="https://www.linkedin.com/jobs/view/2001/",
        ))
        db.commit()

        from app.services.linkedin_browser import LinkedInBrowserService
        svc = LinkedInBrowserService()
        with patch.object(svc, "_scrape_jobs_for_you", new=AsyncMock(return_value=mock_jobs)), \
             patch("playwright.async_api.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=_fake_playwright())
            ok, msg, count = await svc.fetch_jobs(db, test_user.id)

        assert count == 0  # already exists — not re-inserted
        assert db.query(LinkedInJob).filter_by(user_id=test_user.id).count() == 1

    @pytest.mark.asyncio
    async def test_tc_fetch_05_stale_session_triggers_relogin(self, db, test_user, stale_linkedin_session):
        """TC-FETCH-05 Stale session triggers re-login before fetch."""
        from app.services.linkedin_browser import LinkedInBrowserService
        svc = LinkedInBrowserService()
        with patch.object(svc, "login", new=AsyncMock(return_value=(False, "Login failed"))) as mock_login:
            ok, msg, count = await svc.fetch_jobs(db, test_user.id)
        mock_login.assert_called_once()
        assert ok is False
        assert "re-login" in msg.lower()

    def test_tc_fetch_06_get_jobs_returns_paginated(self, db, test_user):
        """TC-FETCH-06 get_jobs returns only is_live=True jobs, paginated."""
        for i in range(5):
            db.add(LinkedInJob(
                user_id=test_user.id, linkedin_job_id=f"3{i:03d}",
                title=f"Role {i}", company="Co",
                job_url=f"https://www.linkedin.com/jobs/view/3{i:03d}/",
                is_live=(i < 4),  # one hidden
            ))
        db.commit()
        from app.services.linkedin_browser import LinkedInBrowserService
        result = LinkedInBrowserService().get_jobs(db, test_user.id, page=1, size=10)
        assert result["total"] == 4
        assert len(result["jobs"]) == 4


# ─────────────────────────────────────────────────────────────────────────────
# Module 3: Application Creation
# ─────────────────────────────────────────────────────────────────────────────

class TestApplicationCreation:
    """TC-APP-* : POST /applications — all creation paths."""

    def test_tc_app_01_create_from_linkedin_url(self, client, db, job_source):
        """TC-APP-01 linkedInPrepare flow: URL+title+company → JobOpportunity created, app linked."""
        payload = {
            "application_url": "https://www.linkedin.com/jobs/view/77777/",
            "job_title": "Head of Engineering",
            "company_name": "NewCo AG",
            "status": "draft",
        }
        res = client.post("/applications", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "draft"
        assert data["job_opportunity_id"] is not None
        # Verify JobOpportunity was auto-created
        opp = db.query(JobOpportunity).filter_by(
            application_url="https://www.linkedin.com/jobs/view/77777/"
        ).first()
        assert opp is not None
        assert opp.title == "Head of Engineering"
        assert opp.description is None  # not populated yet

    def test_tc_app_02_duplicate_url_returns_existing(self, client, db, draft_application):
        """TC-APP-02 Posting the same URL twice returns the existing application."""
        payload = {
            "application_url": draft_application.application_url,
            "status": "draft",
        }
        res1 = client.post("/applications", json=payload)
        res2 = client.post("/applications", json=payload)
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res1.json()["id"] == res2.json()["id"]

    def test_tc_app_03_create_from_job_opportunity_id(self, client, job_opportunity):
        """TC-APP-03 Passing job_opportunity_id links correctly."""
        payload = {"job_opportunity_id": job_opportunity.id, "status": "draft"}
        res = client.post("/applications", json=payload)
        assert res.status_code == 200
        assert res.json()["job_opportunity_id"] == job_opportunity.id

    def test_tc_app_04_invalid_job_opportunity_id(self, client):
        """TC-APP-04 Non-existent job_opportunity_id → 404."""
        payload = {"job_opportunity_id": 99999, "status": "draft"}
        res = client.post("/applications", json=payload)
        assert res.status_code == 404

    def test_tc_app_05_get_application_populates_job_description(self, client, prepared_application):
        """TC-APP-05 GET /applications/{id} surfaces job_description from linked opportunity."""
        res = client.get(f"/applications/{prepared_application.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["job_title"] == "Head of IT"
        assert data["company_name"] == "MegaCorp AG"
        assert len(data.get("job_description", "")) > 100

    def test_tc_app_06_list_applications_belongs_to_user(self, client, prepared_application):
        """TC-APP-06 GET /applications only returns this user's applications."""
        res = client.get("/applications")
        assert res.status_code == 200
        ids = [a["id"] for a in res.json()]
        assert prepared_application.id in ids


# ─────────────────────────────────────────────────────────────────────────────
# Module 4: Job Description Fetching
# ─────────────────────────────────────────────────────────────────────────────

class TestJobDescriptionFetching:
    """TC-DESC-* : All paths through the description-resolution logic in JobPreparationAgent."""

    @pytest.mark.asyncio
    async def test_tc_desc_01_description_in_db_no_scrape(self, db, test_user, draft_application):
        """TC-DESC-01 Description already in JobOpportunity.description → used directly, no scrape."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        with patch.object(agent.extractor, "extract_with_diagnosis") as mock_scrape, \
             patch("agents.job_preparation_agent.LinkedInBrowserService") as mock_li_cls:
            result = await agent.prepare_application(test_user.id, draft_application.id)
        mock_scrape.assert_not_called()
        mock_li_cls.assert_not_called()
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_desc_02_user_pasted_override_used_directly(self, db, test_user, draft_application_no_desc):
        """TC-DESC-02 job_description_override bypasses all scraping and is saved to DB."""
        pasted = "We need a CTO with 10+ years experience in cloud and agile. " * 10
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        with patch.object(agent.extractor, "extract_with_diagnosis") as mock_scrape, \
             patch("agents.job_preparation_agent.LinkedInBrowserService") as mock_li_cls:
            result = await agent.prepare_application(
                test_user.id, draft_application_no_desc.id,
                job_description_override=pasted
            )
        mock_scrape.assert_not_called()
        mock_li_cls.assert_not_called()
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_desc_03_linkedin_scrape_succeeds_and_caches(
        self, db, test_user, linkedin_session, draft_application_no_desc
    ):
        """TC-DESC-03 LinkedIn scrape succeeds → description returned AND saved to JobOpportunity."""
        scraped = "We need an IT Director for digital transformation. " * 20
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        mock_li = MagicMock()
        mock_li.session_status.return_value = {"connected": True}
        mock_li.fetch_job_description = AsyncMock(return_value=scraped)
        with patch("agents.job_preparation_agent.LinkedInBrowserService", return_value=mock_li):
            result = await agent.prepare_application(test_user.id, draft_application_no_desc.id)
        assert result["status"] == "success"
        # Description must be persisted so reprepare skips the scrape
        db.refresh(draft_application_no_desc.job_opportunity)
        assert draft_application_no_desc.job_opportunity.description == scraped

    @pytest.mark.asyncio
    async def test_tc_desc_04_body_text_fallback_when_selectors_fail(
        self, db, test_user, linkedin_session, draft_application_no_desc
    ):
        """TC-DESC-04 All CSS selectors fail but body-text fallback returns description."""
        body_text = "About the job\nWe are looking for an IT Director. " * 30
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        mock_li = MagicMock()
        mock_li.session_status.return_value = {"connected": True}
        # fetch_job_description succeeds via body fallback internally
        mock_li.fetch_job_description = AsyncMock(return_value=body_text)
        with patch("agents.job_preparation_agent.LinkedInBrowserService", return_value=mock_li):
            result = await agent.prepare_application(test_user.id, draft_application_no_desc.id)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_desc_05_all_scrape_fallbacks_fail_returns_422_data(
        self, db, test_user, linkedin_session, draft_application_no_desc
    ):
        """TC-DESC-05 Scrape returns None → error_code=description_required, scrape_status=not_found."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        mock_li = MagicMock()
        mock_li.session_status.return_value = {"connected": True}
        mock_li.fetch_job_description = AsyncMock(return_value=None)
        with patch("agents.job_preparation_agent.LinkedInBrowserService", return_value=mock_li):
            result = await agent.prepare_application(test_user.id, draft_application_no_desc.id)
        assert result["status"] == "error"
        assert result["error_code"] == "description_required"
        assert result["scrape_status"] == "not_found"

    @pytest.mark.asyncio
    async def test_tc_desc_06_stale_session_returns_auth_required(
        self, db, test_user, stale_linkedin_session, draft_application_no_desc
    ):
        """TC-DESC-06 Stale session → connected=False → scrape skipped → auth_required."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        mock_li = MagicMock()
        mock_li.session_status.return_value = {"connected": False, "has_credentials": True}
        with patch("agents.job_preparation_agent.LinkedInBrowserService", return_value=mock_li):
            result = await agent.prepare_application(test_user.id, draft_application_no_desc.id)
        assert result["status"] == "error"
        assert result["error_code"] == "description_required"
        assert result["scrape_status"] == "auth_required"

    @pytest.mark.asyncio
    async def test_tc_desc_07_not_connected_returns_auth_required(
        self, db, test_user, draft_application_no_desc
    ):
        """TC-DESC-07 No LinkedIn session at all → error_code=description_required."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        mock_li = MagicMock()
        mock_li.session_status.return_value = {"connected": False, "has_credentials": False}
        with patch("agents.job_preparation_agent.LinkedInBrowserService", return_value=mock_li):
            result = await agent.prepare_application(test_user.id, draft_application_no_desc.id)
        assert result["status"] == "error"
        assert result["error_code"] == "description_required"

    @pytest.mark.asyncio
    async def test_tc_desc_08_no_url_no_description_returns_no_url(
        self, db, test_user, job_source
    ):
        """TC-DESC-08 Application with no URL and no description → scrape_status=no_url."""
        opp = JobOpportunity(
            source_id=job_source.id, title="Mystery Role", company="Unknown",
            application_url="https://example.com/jobs/mystery", description=None, is_live=True,
        )
        db.add(opp)
        db.flush()
        app = JobApplication(
            user_id=test_user.id, job_opportunity_id=opp.id,
            application_url=None, status="draft",
        )
        db.add(app)
        db.commit()
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        with patch("agents.job_preparation_agent.LinkedInBrowserService") as mock_li_cls:
            mock_li_cls.return_value.session_status.return_value = {"connected": False}
            result = await agent.prepare_application(test_user.id, app.id)
        # non-LinkedIn URL → extraction service
        assert result["status"] == "error"
        assert result["error_code"] == "description_required"

    @pytest.mark.asyncio
    async def test_tc_desc_09_non_linkedin_url_firecrawl_success(
        self, db, test_user, job_source
    ):
        """TC-DESC-09 Non-LinkedIn URL → ExtractionService succeeds → materials prepared."""
        opp = JobOpportunity(
            source_id=job_source.id, title="Backend Engineer", company="TechCo",
            application_url="https://careers.techco.com/jobs/42", description=None, is_live=True,
        )
        db.add(opp)
        db.flush()
        app = JobApplication(
            user_id=test_user.id, job_opportunity_id=opp.id,
            application_url="https://careers.techco.com/jobs/42", status="draft",
        )
        db.add(app)
        db.commit()
        scraped = "We need a Backend Engineer with Python, AWS, and 5+ years experience. " * 15
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        with patch.object(
            agent.extractor, "extract_with_diagnosis",
            new=AsyncMock(return_value={"status": "success", "content": scraped, "reason": ""})
        ):
            result = await agent.prepare_application(test_user.id, app.id)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_desc_10_non_linkedin_auth_wall(self, db, test_user, job_source):
        """TC-DESC-10 Non-LinkedIn URL returns auth wall → 422 auth_required."""
        opp = JobOpportunity(
            source_id=job_source.id, title="Any", company="Any",
            application_url="https://private.com/job/1", description=None, is_live=True,
        )
        db.add(opp)
        db.flush()
        app = JobApplication(
            user_id=test_user.id, job_opportunity_id=opp.id,
            application_url="https://private.com/job/1", status="draft",
        )
        db.add(app)
        db.commit()
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        with patch.object(
            agent.extractor, "extract_with_diagnosis",
            new=AsyncMock(return_value={"status": "auth_required", "content": None,
                                        "reason": "Login required"})
        ):
            result = await agent.prepare_application(test_user.id, app.id)
        assert result["status"] == "error"
        assert result["scrape_status"] == "auth_required"

    @pytest.mark.asyncio
    async def test_tc_desc_11_non_linkedin_expired_posting(self, db, test_user, job_source):
        """TC-DESC-11 Non-LinkedIn URL returns 404/expired → scrape_status=not_found."""
        opp = JobOpportunity(
            source_id=job_source.id, title="Old Job", company="OldCo",
            application_url="https://old.com/job/expired", description=None, is_live=True,
        )
        db.add(opp)
        db.flush()
        app = JobApplication(
            user_id=test_user.id, job_opportunity_id=opp.id,
            application_url="https://old.com/job/expired", status="draft",
        )
        db.add(app)
        db.commit()
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        with patch.object(
            agent.extractor, "extract_with_diagnosis",
            new=AsyncMock(return_value={"status": "not_found", "content": None,
                                        "reason": "This job is no longer available"})
        ):
            result = await agent.prepare_application(test_user.id, app.id)
        assert result["status"] == "error"
        assert result["scrape_status"] == "not_found"

    @pytest.mark.asyncio
    async def test_tc_desc_12_short_content_too_short(self, db, test_user, job_source):
        """TC-DESC-12 Scraped page returns < 200 chars → scrape_status=too_short."""
        opp = JobOpportunity(
            source_id=job_source.id, title="Short", company="Co",
            application_url="https://co.com/jobs/1", description=None, is_live=True,
        )
        db.add(opp)
        db.flush()
        app = JobApplication(
            user_id=test_user.id, job_opportunity_id=opp.id,
            application_url="https://co.com/jobs/1", status="draft",
        )
        db.add(app)
        db.commit()
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        with patch.object(
            agent.extractor, "extract_with_diagnosis",
            new=AsyncMock(return_value={"status": "too_short", "content": None,
                                        "reason": "Only 50 characters returned"})
        ):
            result = await agent.prepare_application(test_user.id, app.id)
        assert result["status"] == "error"
        assert result["scrape_status"] == "too_short"


# ─────────────────────────────────────────────────────────────────────────────
# Module 5: Prepare Pipeline — LLM Phases
# ─────────────────────────────────────────────────────────────────────────────

class TestPreparePipeline:
    """TC-PREP-* : LLM analyze→write→audit→refine loop."""

    @pytest.mark.asyncio
    async def test_tc_prep_01_full_pipeline_approved_first_attempt(
        self, db, test_user, draft_application
    ):
        """TC-PREP-01 All LLM calls succeed, audit approves first time → status=prepared."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        assert result["tailored_cv"] is not None
        assert result["cover_letter"] is not None
        db.refresh(draft_application)
        assert draft_application.status == "prepared"

    @pytest.mark.asyncio
    async def test_tc_prep_02_cover_letter_too_long_triggers_length_guard(
        self, db, test_user, draft_application
    ):
        """TC-PREP-02 CL > 350 words triggers length-guard refinement before audit."""
        long_cl_content = dict(MOCK_TAILORED_CONTENT)
        long_cl_content["cover_letter"] = ("word " * 400 +
            "\n- Achievement one\n- Achievement two\n- Achievement three")
        # LLM sequence: battle_plan → long_cl → refined_cl (short) → audit_ok
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            long_cl_content,
            MOCK_TAILORED_CONTENT,   # refined version
            MOCK_AUDIT_APPROVED,
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        # Refinement was called (4 LLM calls total instead of 3)
        assert llm.generate_json.call_count >= 4

    @pytest.mark.asyncio
    async def test_tc_prep_03_missing_bullets_failsafe_triggers_refinement(
        self, db, test_user, draft_application
    ):
        """TC-PREP-03 CL with no '-' or '*' bullets → fail-safe forces refinement."""
        no_bullets_content = dict(MOCK_TAILORED_CONTENT)
        no_bullets_content["cover_letter"] = (
            "Dear Hiring Manager,\n\n"
            "I am the best candidate. I have lots of experience. Please hire me.\n\n"
            "Best regards,\nAlex"
        )
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            no_bullets_content,
            MOCK_AUDIT_APPROVED,    # audit returns ok but fail-safe overrides
            MOCK_TAILORED_CONTENT,  # refined with bullets
            MOCK_AUDIT_APPROVED,
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_prep_04_audit_rejected_score_triggers_refinement(
        self, db, test_user, draft_application
    ):
        """TC-PREP-04 Audit score < 8 triggers one refinement pass."""
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            MOCK_TAILORED_CONTENT,
            MOCK_AUDIT_REJECTED,     # first audit fails
            MOCK_TAILORED_CONTENT,   # refinement produces better content
            MOCK_AUDIT_APPROVED,     # second audit passes
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        assert llm.generate_json.call_count == 5

    @pytest.mark.asyncio
    async def test_tc_prep_05_hallucination_detected_triggers_refinement(
        self, db, test_user, draft_application
    ):
        """TC-PREP-05 Hallucination in audit forces refinement regardless of score."""
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            MOCK_TAILORED_CONTENT,
            MOCK_AUDIT_HALLUCINATION,  # hallucination found → rejected
            MOCK_TAILORED_CONTENT,     # refinement
            MOCK_AUDIT_APPROVED,       # passes
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_prep_06_max_two_refinement_attempts_respected(
        self, db, test_user, draft_application
    ):
        """TC-PREP-06 Even if audit keeps rejecting, loop stops at max_attempts=2."""
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            MOCK_TAILORED_CONTENT,
            MOCK_AUDIT_REJECTED,     # attempt 1 fails
            MOCK_TAILORED_CONTENT,   # refinement
            MOCK_AUDIT_REJECTED,     # attempt 2 still fails → exits loop anyway
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        # Still saves materials even if not approved after max attempts
        assert result["status"] == "success"
        assert llm.generate_json.call_count == 5

    @pytest.mark.asyncio
    async def test_tc_prep_07_llm_error_returns_500_data(
        self, db, test_user, draft_application
    ):
        """TC-PREP-07 LLM generate_json returns {'error': ...} → prepare returns error."""
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            {"error": "Rate limit exceeded"},
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_tc_prep_08_experience_dates_normalized_to_year_only(
        self, db, test_user, draft_application
    ):
        """TC-PREP-08 Dates like '2025-01 - 2025-06' are normalized to '2025 - 2025'."""
        content_with_month_dates = dict(MOCK_TAILORED_CONTENT)
        content_with_month_dates["tailored_experiences"] = [
            {
                "role": "IT Director", "company": "Acme",
                "dates": "2020-03 - 2025-01",
                "bullets": ["Led transformation."],
            }
        ]
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN,
            content_with_month_dates,
            MOCK_AUDIT_APPROVED,
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        assert "2020" in result["tailored_cv"]
        assert "-03" not in result["tailored_cv"]

    @pytest.mark.asyncio
    async def test_tc_prep_09_analyze_job_uses_full_description(
        self, db, test_user, draft_application
    ):
        """TC-PREP-09 Phase 1 (analyze) is called with the job description as argument."""
        llm = AsyncMock()
        llm.generate_json = AsyncMock(side_effect=[
            MOCK_BATTLE_PLAN, MOCK_TAILORED_CONTENT, MOCK_AUDIT_APPROVED,
        ])
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = llm
        agent.pdf_service = make_mock_pdf()
        with patch.object(agent, "_analyze_job", wraps=agent._analyze_job) as spy:
            await agent.prepare_application(test_user.id, draft_application.id)
        spy.assert_called_once()
        called_desc = spy.call_args[0][0]
        assert len(called_desc) > 100  # must receive meaningful text


# ─────────────────────────────────────────────────────────────────────────────
# Module 6: PDF Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestPDFGeneration:
    """TC-PDF-* : PDF creation paths."""

    @pytest.mark.asyncio
    async def test_tc_pdf_01_cv_and_cl_paths_stored_on_success(
        self, db, test_user, draft_application, tmp_path
    ):
        """TC-PDF-01 Successful PDF generation → cv_path and cl_path stored in DB."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        mock_pdf = make_mock_pdf()
        agent.pdf_service = mock_pdf
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        assert result["cv_path"] is not None
        assert result["cl_path"] is not None
        db.refresh(draft_application)
        assert draft_application.cv_path is not None
        assert draft_application.cl_path is not None

    @pytest.mark.asyncio
    async def test_tc_pdf_02_cv_pdf_failure_still_saves_cl(
        self, db, test_user, draft_application
    ):
        """TC-PDF-02 CV PDF fails but CL PDF succeeds → cl_path saved, cv_path is None."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        mock_pdf = AsyncMock()
        mock_pdf.create_cv_pdf = AsyncMock(return_value=False)  # CV fails
        mock_pdf.create_cl_pdf = AsyncMock(return_value=True)   # CL succeeds
        agent.pdf_service = mock_pdf
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"
        db.refresh(draft_application)
        assert draft_application.cv_path is None
        assert draft_application.cl_path is not None

    @pytest.mark.asyncio
    async def test_tc_pdf_03_no_profile_picture_handled_gracefully(
        self, db, test_user, draft_application
    ):
        """TC-PDF-03 profile_picture_url is None → no crash, PDF still generated."""
        profile = db.query(UserProfile).filter_by(user_id=test_user.id).first()
        profile.profile_picture_url = None
        db.commit()
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_pdf_04_markdown_cv_contains_all_sections(
        self, db, test_user, draft_application
    ):
        """TC-PDF-04 Generated markdown CV includes all expected section headers."""
        from agents.job_preparation_agent import JobPreparationAgent
        agent = JobPreparationAgent(db)
        agent.llm = make_mock_llm()
        agent.pdf_service = make_mock_pdf()
        result = await agent.prepare_application(test_user.id, draft_application.id)
        cv = result["tailored_cv"]
        for section in ["EXPERTISE", "PROFESSIONAL EXPERIENCE", "EDUCATION", "LANGUAGES", "SKILLS"]:
            assert section in cv, f"Expected section '{section}' missing from CV markdown"


# ─────────────────────────────────────────────────────────────────────────────
# Module 7: Full Prepare Integration (API level)
# ─────────────────────────────────────────────────────────────────────────────

class TestPrepareIntegration:
    """TC-INT-* : POST /applications/{id}/prepare via HTTP."""

    def test_tc_int_01_prepare_returns_200_with_materials(self, client, draft_application):
        """TC-INT-01 Happy-path prepare → HTTP 200 with tailored_cv and cover_letter."""
        with patch("app.main.JobPreparationAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.prepare_application = AsyncMock(return_value={
                "status": "success",
                "job_title": "Head of IT",
                "company": "MegaCorp AG",
                "tailored_cv": "# Alex Mueller\nTagline\n\n## EXPERTISE\nGreat IT Director.",
                "cover_letter": "Dear Hiring Manager,\n\n- Achievement\n\nBest,\nAlex",
                "cv_path": "uploads/1/applications/1/CV.pdf",
                "cl_path": "uploads/1/applications/1/CL.pdf",
            })
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{draft_application.id}/prepare")
        assert res.status_code == 200
        data = res.json()
        assert data["tailored_cv"] is not None
        assert data["cover_letter"] is not None

    def test_tc_int_02_description_required_returns_422(self, client, draft_application):
        """TC-INT-02 Agent returns description_required → HTTP 422 with structured detail."""
        with patch("app.main.JobPreparationAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.prepare_application = AsyncMock(return_value={
                "status": "error",
                "error_code": "description_required",
                "scrape_status": "auth_required",
                "message": "Please paste the job description.",
                "url": "https://www.linkedin.com/jobs/view/99999/",
            })
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{draft_application.id}/prepare")
        assert res.status_code == 422
        detail = res.json()["detail"]
        assert detail["error_code"] == "description_required"
        assert detail["scrape_status"] == "auth_required"

    def test_tc_int_03_pasted_description_stored_on_job_opportunity(
        self, client, db, draft_application
    ):
        """TC-INT-03 Pasting a description updates JobOpportunity.description in DB."""
        pasted = "Senior Python Developer needed. Flask, FastAPI, AWS, 5+ years. " * 10
        with patch("app.main.JobPreparationAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.prepare_application = AsyncMock(return_value={
                "status": "success", "job_title": "Dev", "company": "Co",
                "tailored_cv": "# Name\n", "cover_letter": "- bullet",
                "cv_path": None, "cl_path": None,
            })
            MockAgent.return_value = mock_instance
            res = client.post(
                f"/applications/{draft_application.id}/prepare",
                json={"job_description": pasted},
            )
        assert res.status_code == 200
        db.refresh(draft_application.job_opportunity)
        assert draft_application.job_opportunity.description == pasted.strip()

    def test_tc_int_04_prepare_unknown_application_returns_404(self, client):
        """TC-INT-04 Prepare on non-existent application → 404."""
        res = client.post("/applications/99999/prepare")
        assert res.status_code == 404

    def test_tc_int_05_llm_error_returns_500(self, client, draft_application):
        """TC-INT-05 LLM crash inside prepare → HTTP 500."""
        with patch("app.main.JobPreparationAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.prepare_application = AsyncMock(return_value={
                "status": "error",
                "message": "LLM Error: Rate limit exceeded",
            })
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{draft_application.id}/prepare")
        assert res.status_code == 500

    def test_tc_int_06_patch_application_updates_fields(self, client, prepared_application):
        """TC-INT-06 PATCH /applications/{id} updates notes and status."""
        with patch("app.main.JobPreparationAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.regenerate_pdfs_from_text = AsyncMock(return_value={
                "status": "success", "cv_path": "new_cv.pdf", "cl_path": "new_cl.pdf"
            })
            MockAgent.return_value = mock_instance
            res = client.patch(
                f"/applications/{prepared_application.id}",
                json={"status": "interviewing", "notes": "Great interview scheduled"},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "interviewing"
        assert data["notes"] == "Great interview scheduled"


# ─────────────────────────────────────────────────────────────────────────────
# Module 8: Auto-Apply Engine
# ─────────────────────────────────────────────────────────────────────────────

class TestAutoApply:
    """TC-AUTO-* : POST /applications/{id}/apply guards and outcomes."""

    def test_tc_auto_01_apply_without_prepared_materials_returns_400(
        self, client, draft_application
    ):
        """TC-AUTO-01 Applying before prepare → 400 with clear message."""
        res = client.post(f"/applications/{draft_application.id}/apply")
        assert res.status_code == 400
        assert "Prep" in res.json()["detail"] or "prepared" in res.json()["detail"].lower()

    def test_tc_auto_02_apply_already_applying_returns_409(
        self, client, db, prepared_application
    ):
        """TC-AUTO-02 Concurrent apply attempt (status=applying) → 409 Conflict."""
        prepared_application.status = "applying"
        db.commit()
        res = client.post(f"/applications/{prepared_application.id}/apply")
        assert res.status_code == 409

    def test_tc_auto_03_apply_no_url_returns_400(self, client, db, test_user):
        """TC-AUTO-03 Prepared application with no URL → 400 (nowhere to apply)."""
        app = JobApplication(
            user_id=test_user.id,
            application_url=None,
            job_opportunity_id=None,
            status="prepared",
            tailored_cv="# Name\n",
            cover_letter="- bullet",
        )
        db.add(app)
        db.commit()
        res = client.post(f"/applications/{app.id}/apply")
        assert res.status_code == 400
        assert "URL" in res.json()["detail"]

    def test_tc_auto_04_successful_apply_returns_200(self, client, prepared_application):
        """TC-AUTO-04 Auto-apply succeeds → HTTP 200 with status=applied."""
        with patch("app.main.AutoApplyAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run_automation = AsyncMock(return_value={
                "status": "success",
                "message": "Application submitted via LinkedIn Easy Apply",
                "screenshot_path": "scratch/apply_confirm_99.png",
            })
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{prepared_application.id}/apply")
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_tc_auto_05_agent_error_returns_500(self, client, prepared_application):
        """TC-AUTO-05 Auto-apply agent crashes → HTTP 500."""
        with patch("app.main.AutoApplyAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run_automation = AsyncMock(return_value={
                "status": "error",
                "message": "Browser crashed unexpectedly",
            })
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{prepared_application.id}/apply")
        assert res.status_code == 500

    def test_tc_auto_06_apply_nonexistent_application_404(self, client):
        """TC-AUTO-06 Apply on missing application → 404."""
        res = client.post("/applications/99999/apply")
        assert res.status_code == 404

    def test_tc_auto_07_intervention_required_stores_data(
        self, client, db, prepared_application
    ):
        """TC-AUTO-07 Apply returns intervention_required → data stored on application."""
        intervention_data = {
            "status": "intervention_required",
            "message": "Unable to answer: 'Do you have a PhD?'",
            "intervention_field": "education_level",
        }
        with patch("app.main.AutoApplyAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run_automation = AsyncMock(return_value=intervention_data)
            MockAgent.return_value = mock_instance
            res = client.post(f"/applications/{prepared_application.id}/apply")
        # Intervention is a user-facing result, not a server error
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "intervention_required"


# ─────────────────────────────────────────────────────────────────────────────
# Module 9: ExtractionService Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractionService:
    """TC-EXT-* : Content classification and URL fetching logic."""

    def test_tc_ext_01_empty_content_returns_empty_status(self):
        """TC-EXT-01 None/empty content → status=empty."""
        from app.services.extraction_service import _classify_content
        result = _classify_content("https://example.com", "")
        assert result["status"] == "empty"
        assert result["content"] is None

    def test_tc_ext_02_auth_wall_phrase_detected(self):
        """TC-EXT-02 Page contains 'sign in to' → status=auth_required."""
        from app.services.extraction_service import _classify_content
        result = _classify_content("https://example.com", "sign in to view this job posting" * 5)
        assert result["status"] == "auth_required"

    def test_tc_ext_03_linkedin_auth_wall_specific_message(self):
        """TC-EXT-03 LinkedIn auth wall gives LinkedIn-specific reason message."""
        from app.services.extraction_service import _classify_content
        result = _classify_content(
            "https://www.linkedin.com/jobs/view/123",
            "Join LinkedIn to see this job"
        )
        assert result["status"] == "auth_required"
        assert "LinkedIn" in result["reason"]

    def test_tc_ext_04_expired_job_detected(self):
        """TC-EXT-04 'No longer accepting applications' → status=not_found."""
        from app.services.extraction_service import _classify_content
        result = _classify_content(
            "https://jobs.co.com/role/5",
            "This job is no longer accepting applications. " * 10
        )
        assert result["status"] == "not_found"

    def test_tc_ext_05_content_too_short(self):
        """TC-EXT-05 Content < 200 chars (no auth/404 phrases) → status=too_short."""
        from app.services.extraction_service import _classify_content
        result = _classify_content("https://jobs.co.com/role/5", "Short content here.")
        assert result["status"] == "too_short"

    def test_tc_ext_06_good_content_returns_success(self):
        """TC-EXT-06 Sufficient clean content (>200 chars, no blocked phrases) → success."""
        from app.services.extraction_service import _classify_content
        good_content = "We are hiring a Senior Engineer. " * 20
        result = _classify_content("https://jobs.co.com/role/5", good_content)
        assert result["status"] == "success"
        assert result["content"] == good_content

    @pytest.mark.asyncio
    async def test_tc_ext_07_jina_fallback_when_firecrawl_returns_none(self):
        """TC-EXT-07 When Firecrawl returns None, Jina is called."""
        from app.services.extraction_service import ExtractionService
        svc = ExtractionService()
        good = "Great engineering role with Python and AWS. " * 20
        with patch.object(svc, "_fetch_firecrawl", new=AsyncMock(return_value=None)), \
             patch.object(svc, "_fetch_jina", new=AsyncMock(return_value=good)):
            result = await svc.extract_with_diagnosis("https://example.com/job/1")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tc_ext_08_both_scrapers_fail_returns_error(self):
        """TC-EXT-08 Both Firecrawl and Jina fail → status=error."""
        from app.services.extraction_service import ExtractionService
        svc = ExtractionService()
        with patch.object(svc, "_fetch_firecrawl", new=AsyncMock(return_value=None)), \
             patch.object(svc, "_fetch_jina", new=AsyncMock(return_value=None)):
            result = await svc.extract_with_diagnosis("https://example.com/job/1")
        assert result["status"] == "error"
        assert result["content"] is None

    @pytest.mark.asyncio
    async def test_tc_ext_09_no_firecrawl_key_skips_to_jina(self):
        """TC-EXT-09 No Firecrawl API key → goes straight to Jina."""
        from app.services.extraction_service import ExtractionService
        svc = ExtractionService()
        svc.firecrawl_key = None
        good = "Python backend engineer position. " * 20
        with patch.object(svc, "_fetch_firecrawl", new=AsyncMock(return_value="SHOULD_NOT_CALL")) as mock_fc, \
             patch.object(svc, "_fetch_jina", new=AsyncMock(return_value=good)):
            result = await svc.extract_with_diagnosis("https://example.com/job/1")
        mock_fc.assert_not_called()
        assert result["status"] == "success"


# ─────────────────────────────────────────────────────────────────────────────
# Module 10: LLM Bridge Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMBridge:
    """TC-LLM-* : JSON parsing, model fallback, provider routing."""

    def test_tc_llm_01_parse_json_from_code_block(self):
        """TC-LLM-01 JSON wrapped in ```json``` fences is correctly extracted."""
        from agents.core.llm_bridge import _parse_json
        text = '```json\n{"key": "value", "num": 42}\n```'
        result = _parse_json(text)
        assert result == {"key": "value", "num": 42}

    def test_tc_llm_02_parse_json_bare_braces(self):
        """TC-LLM-02 JSON without fences is extracted by brace-matching."""
        from agents.core.llm_bridge import _parse_json
        text = 'Some preamble {"a": 1, "b": [1, 2, 3]} trailing text'
        result = _parse_json(text)
        assert result["a"] == 1
        assert result["b"] == [1, 2, 3]

    def test_tc_llm_03_parse_json_array_at_root(self):
        """TC-LLM-03 Root-level JSON array is parsed correctly."""
        from agents.core.llm_bridge import _parse_json
        result = _parse_json('[{"id": 1}, {"id": 2}]')
        assert isinstance(result, list)
        assert len(result) == 2

    def test_tc_llm_04_unparseable_text_returns_error_dict(self):
        """TC-LLM-04 Non-JSON response returns {'error': ..., 'raw': ...}."""
        from agents.core.llm_bridge import _parse_json
        result = _parse_json("I cannot provide a JSON response for this.")
        assert "error" in result

    def test_tc_llm_05_gemini_model_list_no_deprecated_names(self):
        """TC-LLM-05 No deprecated gemini-2.0-flash-lite in the model registry."""
        from agents.core.llm_bridge import _GEMINI_MODELS
        all_models = [m for tier_list in _GEMINI_MODELS.values() for m in tier_list]
        assert "gemini-2.0-flash-lite" not in all_models, \
            "gemini-2.0-flash-lite is deprecated (shuts down June 1 2026)"
        assert "gemini-2.5-flash-lite" not in all_models, \
            "gemini-2.5-flash-lite does not exist; use gemini-3.1-flash-lite"

    def test_tc_llm_06_gemini_model_list_primary_is_35_flash(self):
        """TC-LLM-06 MICRO and VISION primary model is gemini-3.5-flash (latest GA)."""
        from agents.core.llm_bridge import _GEMINI_MODELS, LLMTier
        assert _GEMINI_MODELS[LLMTier.MICRO][0] == "gemini-3.5-flash"
        assert _GEMINI_MODELS[LLMTier.VISION][0] == "gemini-3.5-flash"

    def test_tc_llm_07_bridge_not_available_without_api_key(self):
        """TC-LLM-07 LLMBridge.is_available() is False when no API key provided."""
        from agents.core.llm_bridge import LLMBridge
        bridge = LLMBridge(provider="gemini", gemini_api_key=None)
        assert bridge.is_available() is False

    @pytest.mark.asyncio
    async def test_tc_llm_08_text_call_returns_error_when_not_available(self):
        """TC-LLM-08 text() call when not configured returns error dict."""
        from agents.core.llm_bridge import LLMBridge, LLMTier
        bridge = LLMBridge(provider="gemini", gemini_api_key=None)
        result = await bridge.text("Give me JSON", LLMTier.MICRO)
        assert "error" in result


# ─────────────────────────────────────────────────────────────────────────────
# Module 11: ApplyOrchestrator Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyOrchestratorEngine:
    """TC-AO-* : ApplyOrchestrator state machine and stuck-detection behaviour."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_mock_page(url="https://www.linkedin.com/jobs/view/99999/", apply_buttons=None):
        """Minimal Playwright page mock: no overlays, no success elements by default."""
        page = AsyncMock()
        page.url = url
        page.is_closed = MagicMock(return_value=False)
        ctx = MagicMock()
        ctx.pages = [page]
        page.context = ctx
        page.title = AsyncMock(return_value="Head of IT | LinkedIn")
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=apply_buttons or [])
        page.evaluate = AsyncMock(return_value=None)
        return page

    @staticmethod
    def _make_analysis(state_value, step_label="", confidence=90, apply_btn=None):
        """Build a PageAnalysis without running PageAnalyst."""
        from agents.apply_engine.page_analyst import PageAnalysis
        return PageAnalysis(
            {
                "state": state_value,
                "confidence": confidence,
                "step_label": step_label,
                "apply_button_id": apply_btn,
            },
            [],
        )

    @staticmethod
    def _make_apply_button():
        """Minimal mock of a visible Playwright element for an Easy Apply button."""
        btn = AsyncMock()
        btn.is_visible = AsyncMock(return_value=True)
        btn.get_attribute = AsyncMock(return_value="Easy Apply")
        btn.inner_text = AsyncMock(return_value="Easy Apply")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.click = AsyncMock()
        return btn

    @staticmethod
    def _make_orchestrator():
        """Return an ApplyOrchestrator with LLM initialisation patched out."""
        from agents.apply_engine.orchestrator import ApplyOrchestrator
        with patch("agents.core.base_agent.build_bridge_from_settings", return_value=MagicMock()):
            return ApplyOrchestrator()

    # ── Tests ─────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_tc_ao_01_no_apply_button_triggers_intervention(self):
        """TC-AO-01 No Easy Apply button found on job page → immediate INTERVENTION."""
        page = self._make_mock_page()
        analysis = self._make_analysis("job_description", confidence=95)

        with patch("agents.apply_engine.orchestrator._human_delay", new=AsyncMock()):
            orch = self._make_orchestrator()
            orch._analyst.analyse = AsyncMock(return_value=analysis)

            result = await orch.run(page, {"url": "https://www.linkedin.com/jobs/view/99999/"})

        assert result.intervention is True
        assert result.success is False
        assert "No Apply button found" in result.message

    @pytest.mark.asyncio
    async def test_tc_ao_02_form_bounces_back_triggers_stuck_intervention(self):
        """TC-AO-02 FormFiller says navigated=True but page returns same 'Job Details' state 3 times → stuck intervention."""
        page = self._make_mock_page()
        job_details = self._make_analysis("form_step", step_label="Job Details", confidence=90)

        with patch("agents.apply_engine.orchestrator._human_delay", new=AsyncMock()):
            orch = self._make_orchestrator()
            orch._analyst.analyse = AsyncMock(return_value=job_details)
            orch._filler.fill_step = AsyncMock(return_value={"navigated": True})

            result = await orch.run(page, {"url": "https://www.linkedin.com/jobs/view/99999/"})

        assert result.intervention is True
        assert result.success is False
        assert "Job Details" in result.message

    @pytest.mark.asyncio
    async def test_tc_ao_03_contact_info_step_completes_to_success(self):
        """TC-AO-03 Job description → click Easy Apply → fill Contact Info → success page confirmed."""
        apply_btn = self._make_apply_button()
        page = self._make_mock_page(apply_buttons=[apply_btn])

        job_desc = self._make_analysis("job_description", confidence=95)
        contact_info = self._make_analysis("form_step", step_label="Contact Info", confidence=90)
        success = self._make_analysis("success", confidence=100)

        with patch("agents.apply_engine.orchestrator._human_delay", new=AsyncMock()):
            orch = self._make_orchestrator()
            orch._analyst.analyse = AsyncMock(side_effect=[job_desc, contact_info, success])
            orch._filler.fill_step = AsyncMock(return_value={"navigated": True})

            result = await orch.run(page, {"url": "https://www.linkedin.com/jobs/view/99999/"})

        assert result.success is True
        assert result.intervention is False

    @pytest.mark.asyncio
    async def test_tc_ao_04_full_linkedin_easy_apply_happy_path(self):
        """TC-AO-04 Full LinkedIn Easy Apply: job desc → Contact Info → Job Details → Review → success."""
        apply_btn = self._make_apply_button()
        page = self._make_mock_page(apply_buttons=[apply_btn])

        analyses = [
            self._make_analysis("job_description", confidence=95),
            self._make_analysis("form_step", step_label="Contact Info", confidence=90),
            self._make_analysis("form_step", step_label="Job Details", confidence=90),
            self._make_analysis("review", confidence=90),
            self._make_analysis("success", confidence=100),
        ]

        with patch("agents.apply_engine.orchestrator._human_delay", new=AsyncMock()):
            orch = self._make_orchestrator()
            orch._analyst.analyse = AsyncMock(side_effect=analyses)
            orch._filler.fill_step = AsyncMock(return_value={"navigated": True})

            result = await orch.run(page, {
                "url": "https://www.linkedin.com/jobs/view/99999/",
                "tailored_cv": "# Alex Mueller\nIT Director",
                "cover_letter": "Dear Hiring Manager,\n\nI am a perfect fit.\n\nBest,\nAlex",
            })

        assert result.success is True
        assert result.intervention is False
        assert orch._filler.fill_step.call_count == 3

    def test_tc_ao_05_overlay_selectors_do_not_contain_advancement_buttons(self):
        """TC-AO-05 _OVERLAY_SELECTORS must not include text that could submit forms or trigger LinkedIn signup."""
        from agents.apply_engine.orchestrator import _OVERLAY_SELECTORS
        # Form-advancement patterns AND LinkedIn-specific signup/join CTAs
        dangerous_patterns = [
            "next", "submit", "apply", "continue", "weiter", "suivant",
            "agree & join",  # LinkedIn's signup CTA — clicks it on /signup/cold-join pages
        ]
        violations = [
            sel for sel in _OVERLAY_SELECTORS
            if "has-text" in sel.lower()
            and any(pat in sel.lower() for pat in dangerous_patterns)
        ]
        assert not violations, (
            f"Overlay selectors that could advance or submit forms: {violations}"
        )

    @pytest.mark.asyncio
    async def test_tc_ao_06_stuck_message_uses_step_label_not_state_value(self):
        """TC-AO-06 Intervention message shows step_label ('Job Details') not raw state.value ('form_step')."""
        page = self._make_mock_page()
        job_details = self._make_analysis("form_step", step_label="Job Details", confidence=90)

        with patch("agents.apply_engine.orchestrator._human_delay", new=AsyncMock()):
            orch = self._make_orchestrator()
            orch._analyst.analyse = AsyncMock(return_value=job_details)
            orch._filler.fill_step = AsyncMock(return_value={"navigated": True})

            result = await orch.run(page, {"url": "https://www.linkedin.com/jobs/view/99999/"})

        assert result.intervention is True
        assert "Job Details" in result.message
        assert "form_step" not in result.message


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fake_playwright():
    """Minimal Playwright mock so fetch_jobs doesn't open a real browser."""
    pw = MagicMock()
    browser = AsyncMock()
    ctx = AsyncMock()
    page = AsyncMock()
    ctx.new_page = AsyncMock(return_value=page)
    browser.new_context = AsyncMock(return_value=ctx)
    pw.chromium.launch = AsyncMock(return_value=browser)
    pw.__aexit__ = AsyncMock(return_value=None)
    return pw
