"""
Job Finder Agent — two-phase pipeline.

Phase 1  ingest_jobs(country)          — country-level, no user context
         Download all jobs from validated sources, apply quality filters,
         persist raw JobOpportunity records (user_id=None).

Phase 2  align_jobs_to_user(user_id)   — user-specific
         Score recent JobOpportunity records against profile,
         create / update JobMatch records.
"""

import json
import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.models.database import JobOpportunity, JobSource, User, UserProfile, JobMatch
from app.services.llm_analysis import LLMAnalysisService
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country-level city blacklists for Phase 1 noise reduction
# ---------------------------------------------------------------------------
CITY_BLACKLISTS: Dict[str, List[str]] = {
    "Switzerland": ["taipei", "shanghai", "hyderabad", "bangalore", "bengaluru",
                    "mumbai", "hong kong", "tokyo", "seoul", "new delhi", "beijing",
                    "jakarta", "kuala lumpur", "dubai", "abu dhabi"],
    "Germany":     ["taipei", "shanghai", "hyderabad", "bangalore", "bengaluru",
                    "mumbai", "hong kong", "tokyo", "seoul", "new delhi", "beijing"],
    "UK":          ["taipei", "shanghai", "hyderabad", "bangalore", "bengaluru",
                    "mumbai", "hong kong", "tokyo", "seoul", "new delhi", "beijing"],
    "India":       ["taipei", "shanghai", "hong kong", "tokyo", "seoul", "beijing",
                    "london", "new york", "san francisco", "dubai"],
    "Singapore":   ["taipei", "shanghai", "beijing", "new delhi", "tokyo"],
    "Netherlands": ["taipei", "shanghai", "hyderabad", "bangalore", "mumbai", "beijing"],
    "France":      ["taipei", "shanghai", "hyderabad", "bangalore", "mumbai", "beijing"],
    "USA":         ["taipei", "shanghai", "hyderabad", "bangalore", "mumbai", "beijing"],
}

# Job-title nouns used to judge whether a short title is a real job
JOB_NOUNS = {
    'engineer', 'manager', 'lead', 'developer', 'consultant', 'analyst',
    'specialist', 'assistant', 'director', 'officer', 'architect', 'expert',
    'coordinator', 'intern', 'praktikum', 'lehre', 'leiter', 'techniker',
    'verkäufer', 'monteur', 'mitarbeiter', 'accountant', 'hr', 'nurse',
    'doctor', 'teacher', 'admin', 'clerk', 'head', 'representative',
    'scientist', 'technician', 'designer', 'researcher', 'strategist',
    'executive', 'president', 'vp', 'cto', 'cfo', 'coo', 'ceo',
}

JUNK_KEYWORDS = {
    "cookie", "faq", "privacy", "settings", "terms", "policy", "feedback",
    "newsletter", "contact us", "dashboard", "login", "register",
    "forgot password", "results for", "search categories", "bestellen",
    "abo", "subscribe", "sort ascending", "sort descending", "sort by",
    "view all", "next page", "previous page", "inhalt", "summary",
    "navigation", "menu", "footer", "header", "this month", "last two weeks",
    "last 24h", "anytime", "posted within", "relevance", "imprint",
    "impressum", "legal notice", "copyright", "home", "search for",
    "finde deinen job", "find your job", "bewerben", "kategorien",
    "search jobs", "karriere", "vacancies at", "search open",
    "open positions", "current openings", "all jobs", "explore jobs",
    "search and apply", "date posted", "this week", "view jobs in",
    "apply now", "work at",
}

GENERIC_SECTION_TITLES = {
    "vacancies", "jobs", "positions", "openings", "stellen",
    "stellenangebote", "search open", "karriere",
}


# ---------------------------------------------------------------------------
# City lookup used for location detection
# ---------------------------------------------------------------------------
CITY_MAP: Dict[str, List[str]] = {
    "Switzerland": [
        "Basel", "Zürich", "Zurich", "Geneva", "Genève", "Bern", "Luzern",
        "Lucerne", "Lugano", "Zug", "Lausanne", "Winterthur", "St. Gallen",
        "Vaud", "Valais", "Fribourg", "Neuchâtel", "Jura",
    ],
    "Germany": [
        "Berlin", "Munich", "München", "Hamburg", "Frankfurt", "Cologne",
        "Köln", "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund", "Essen",
        "Bremen",
    ],
    "UK": [
        "London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Edinburgh",
        "Bristol", "Liverpool", "Sheffield", "Newcastle",
    ],
    "India": [
        "Mumbai", "Bangalore", "Bengaluru", "Delhi", "Hyderabad", "Chennai",
        "Pune", "Kolkata", "Ahmedabad", "Noida", "Gurgaon",
    ],
    "Singapore": ["Singapore"],
    "Netherlands": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"],
    "France": ["Paris", "Lyon", "Marseille", "Bordeaux", "Toulouse", "Lille", "Nantes"],
    "USA": ["New York", "San Francisco", "Seattle", "Chicago", "Los Angeles",
            "Boston", "Austin", "Denver", "Atlanta"],
}


class JobFinderAgent:
    """Two-phase job discovery: ingest first, align later."""

    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMAnalysisService()

    # =========================================================================
    # PHASE 1 — Raw ingestion (no user context)
    # =========================================================================

    async def ingest_jobs(self, country: str) -> Dict[str, Any]:
        """
        Download all live jobs from every validated source for *country*.
        Applies quality filters (noise, junk, CJK, location sanity).
        Persists JobOpportunity rows (user_id=None, relevance_score=0).
        Returns ingestion statistics.
        """
        from app.services.ingestion_service import IngestionService

        # Load all active, non-invalid sources for this country
        sources_query = (
            self.db.query(JobSource)
            .filter(
                JobSource.is_active == True,
                JobSource.maturity_level != "invalid",
            )
        )
        if country:
            sources_query = sources_query.filter(JobSource.country == country)
        active_sources = sources_query.all()

        if not active_sources:
            logger.warning(f"No active sources found for country={country}")
            return {"status": "no_sources", "country": country,
                    "sources_searched": 0, "raw_found": 0,
                    "new_jobs": 0, "updated_jobs": 0}

        fallback_source_id = active_sources[0].id

        sources_for_ingestion = [
            {"name": s.name, "url": s.url, "source_type": s.source_type, "id": s.id}
            for s in active_sources
        ]

        logger.info(f"Phase 1 — ingesting from {len(sources_for_ingestion)} sources for {country}")

        ingestor = IngestionService()
        ingested = await ingestor.ingest_all_sources(
            sources_for_ingestion,
            location_filter=country,
            max_concurrent=10,
        )

        logger.info(f"Phase 1 — raw results: {len(ingested)}")

        # URL deduplication
        unique_results, seen_urls = [], set()
        for r in ingested:
            if r.url and r.url not in seen_urls:
                unique_results.append(r)
                seen_urls.add(r.url)

        logger.info(f"Phase 1 — unique candidates after dedup: {len(unique_results)}")

        # Quality-filter and persist
        city_blacklist = CITY_BLACKLISTS.get(country, [])
        new_count = 0
        updated_count = 0

        for candidate in unique_results:
            job_url = candidate.url
            source_db_id = getattr(candidate, "source_db_id", None) or fallback_source_id

            # --- Title / company split ---
            raw_title = candidate.title or ""
            if "@" in raw_title:
                job_title = raw_title.split("@")[0].strip()
                company_name = raw_title.split("@")[-1].strip()
            else:
                job_title = raw_title.strip()
                company_name = "Unknown"

            t_lower = job_title.lower()
            u_lower = job_url.lower()

            # 1. Junk URL / title
            if any(w in t_lower for w in JUNK_KEYWORDS) or any(w in u_lower for w in JUNK_KEYWORDS):
                continue

            # 2. CJK characters → non-target market leak
            if re.search(r"[一-鿿぀-ゟ゠-ヿ]", job_title):
                continue

            # 3. City blacklist — job clearly not in target country
            if any(city in t_lower for city in city_blacklist):
                continue

            # 4. Generic section header (not an individual job)
            if t_lower.strip() in GENERIC_SECTION_TITLES:
                continue

            # 5. Jobness heuristic — real jobs have specific titles
            words = [w for w in t_lower.split() if len(w) > 2]
            if len(words) < 5 and not any(noun in t_lower for noun in JOB_NOUNS):
                continue
            title_words = [w for w in t_lower.split() if len(w) > 1]
            if len(title_words) < 2 and t_lower not in JOB_NOUNS:
                continue

            # --- Extract metadata from job content (no profile needed) ---
            loc = self._detect_location(job_title, candidate.snippet or "", country)
            metadata = self._detect_job_metadata(job_title, candidate.snippet or "")

            # --- Upsert JobOpportunity (shared market record) ---
            try:
                existing = self.db.query(JobOpportunity).filter(
                    JobOpportunity.application_url == job_url
                ).first()

                if not existing:
                    new_job = JobOpportunity(
                        user_id=None,
                        source_id=source_db_id,
                        title=job_title,
                        company=company_name,
                        location=loc,
                        job_type=metadata["job_type"],
                        work_mode=metadata["work_mode"],
                        experience_level=metadata["experience_level"],
                        application_url=job_url,
                        description=candidate.snippet or "",
                        relevance_score=0,
                        is_live=True,
                        is_verified=False,
                        first_seen_at=datetime.utcnow(),
                    )
                    self.db.add(new_job)
                    self.db.flush()
                    new_count += 1
                else:
                    # Enrich existing record with better data where available
                    curr_loc = (existing.location or "").strip().lower()
                    new_loc = loc.strip().lower()
                    if curr_loc in ("", country.lower(), "unknown") and new_loc not in ("", country.lower(), "unknown"):
                        existing.location = loc
                    if existing.job_type in (None, "Permanent") and metadata["job_type"] != "Permanent":
                        existing.job_type = metadata["job_type"]
                    if existing.work_mode in (None, "Hybrid") and metadata["work_mode"] != "Hybrid":
                        existing.work_mode = metadata["work_mode"]
                    if existing.experience_level in (None, "Mid-Senior Level") and metadata["experience_level"] != "Mid-Senior Level":
                        existing.experience_level = metadata["experience_level"]
                    if len(candidate.snippet or "") > len(existing.description or ""):
                        existing.description = candidate.snippet
                    updated_count += 1

                self.db.commit()

            except Exception as e:
                self.db.rollback()
                logger.error(f"Error saving job {job_url}: {e}")

        logger.info(f"Phase 1 complete — new={new_count}, updated={updated_count}")

        return {
            "status": "completed",
            "country": country,
            "sources_searched": len(sources_for_ingestion),
            "raw_found": len(ingested),
            "unique_candidates": len(unique_results),
            "new_jobs": new_count,
            "updated_jobs": updated_count,
        }

    # =========================================================================
    # PHASE 2 — User alignment (scoring + JobMatch)
    # =========================================================================

    async def align_jobs_to_user(
        self, user_id: int, deep_check: bool = False
    ) -> Dict[str, Any]:
        """
        Score all recent JobOpportunity records against the user's profile.
        Creates / updates JobMatch rows.  Optionally runs LLM deep-check on
        the top candidates.
        """
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if not profile:
            return {"status": "error", "message": "User profile not found"}

        # All live jobs from the last 14 days
        cutoff = datetime.utcnow() - timedelta(days=14)
        jobs = (
            self.db.query(JobOpportunity)
            .filter(
                JobOpportunity.is_live == True,
                JobOpportunity.first_seen_at >= cutoff,
            )
            .all()
        )

        logger.info(f"Phase 2 — scoring {len(jobs)} jobs for user {user_id}")

        new_matches = 0
        updated_matches = 0
        top_score = 0

        for job in jobs:
            score = self._calculate_heuristic_score(
                job.title, job.description or "", profile
            )
            top_score = max(top_score, score)

            existing_match = self.db.query(JobMatch).filter(
                JobMatch.job_opportunity_id == job.id,
                JobMatch.user_id == user_id,
            ).first()

            if not existing_match:
                self.db.add(JobMatch(
                    user_id=user_id,
                    job_opportunity_id=job.id,
                    relevance_score=score,
                    is_verified=False,
                    match_notes=f"Heuristic: {score}%",
                ))
                new_matches += 1
            else:
                existing_match.relevance_score = score
                updated_matches += 1

            if new_matches % 100 == 0 and new_matches > 0:
                self.db.flush()

        self.db.commit()

        # Optional LLM deep-check on top candidates
        deep_verified = 0
        if deep_check:
            deep_verified = await self._deep_check_top_candidates(
                user_id, profile, cutoff
            )

        logger.info(
            f"Phase 2 complete — new_matches={new_matches}, "
            f"updated={updated_matches}, top_score={top_score}, "
            f"deep_verified={deep_verified}"
        )

        return {
            "status": "completed",
            "jobs_scored": len(jobs),
            "new_matches": new_matches,
            "updated_matches": updated_matches,
            "top_score": top_score,
            "deep_verified": deep_verified,
        }

    async def _deep_check_top_candidates(
        self, user_id: int, profile: UserProfile, cutoff: datetime
    ) -> int:
        """Run LLM alignment on top-scoring candidates not yet verified."""
        from app.services.extraction_service import ExtractionService
        extractor = ExtractionService()

        top_matches = (
            self.db.query(JobMatch, JobOpportunity)
            .join(JobOpportunity, JobMatch.job_opportunity_id == JobOpportunity.id)
            .filter(
                JobMatch.user_id == user_id,
                JobMatch.is_verified == False,
                JobMatch.relevance_score >= 55,
                JobOpportunity.first_seen_at >= cutoff,
            )
            .order_by(JobMatch.relevance_score.desc())
            .limit(20)
            .all()
        )

        verified = 0
        for match, job in top_matches:
            try:
                md = await extractor.extract_markdown(job.application_url)
                if not md:
                    md = f"Title: {job.title}\n{job.description or ''}"
                analysis = await self._verify_alignment_robust(md, profile)
                if isinstance(analysis, dict) and analysis.get("page_type") == "single_job":
                    match.is_verified = True
                    match.relevance_score = analysis.get("match_score", match.relevance_score)
                    match.match_notes = analysis.get("reason", "")
                    verified += 1
            except Exception as e:
                logger.debug(f"Deep-check failed for {job.application_url}: {e}")

        self.db.commit()
        return verified

    # =========================================================================
    # Target scoring (standalone — called from "Target Scoring" button)
    # =========================================================================

    async def score_jobs_for_user(
        self, user_id: int, source_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Re-score existing JobOpportunity records for a user (last 30 days)."""
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        if not profile:
            return {"status": "error", "message": "User profile not found"}

        query = self.db.query(JobOpportunity).filter(
            JobOpportunity.first_seen_at >= datetime.utcnow() - timedelta(days=30)
        )
        if source_country:
            query = (
                query
                .join(JobSource, JobOpportunity.source_id == JobSource.id)
                .filter(JobSource.country == source_country)
            )
        jobs = query.all()

        count = 0
        for job in jobs:
            score = self._calculate_heuristic_score(
                job.title, job.description or "", profile
            )
            match = self.db.query(JobMatch).filter(
                JobMatch.user_id == user_id,
                JobMatch.job_opportunity_id == job.id,
            ).first()
            if match:
                match.relevance_score = score
            else:
                self.db.add(JobMatch(
                    user_id=user_id,
                    job_opportunity_id=job.id,
                    relevance_score=score,
                    is_verified=False,
                ))
            count += 1
            if count % 50 == 0:
                self.db.flush()

        self.db.commit()
        return {"status": "success", "scored_count": count}

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _calculate_heuristic_score(
        self, title: str, snippet: str, profile: UserProfile
    ) -> int:
        try:
            from app.config import HEURISTIC_WEIGHTS
        except ImportError:
            HEURISTIC_WEIGHTS = {}

        score = HEURISTIC_WEIGHTS.get("BASE_SCORE", 20)
        t_lower = title.lower()
        s_lower = snippet.lower()

        # 1. Target title match
        target_title = (profile.desired_job_title or "").lower()
        target_words = [w for w in target_title.split() if len(w) >= 2]
        if target_title:
            if target_title in t_lower:
                score += HEURISTIC_WEIGHTS.get("TITLE_MATCH", 15)
            elif any(
                re.search(r"(?:\b|\s)" + re.escape(tw) + r"(?:\b|\s)", t_lower)
                for tw in target_words
            ):
                score += HEURISTIC_WEIGHTS.get("TITLE_MATCH", 15)

        # 2. Seniority
        senior_kw = ["director", "head", "lead", "senior", "manager", "vp",
                     "chief", "principal", "expert", "chef", "leitung", "leiter"]
        if any(w in t_lower for w in senior_kw):
            score += HEURISTIC_WEIGHTS.get("SENIORITY_MATCH", 15)

        # 3. Location
        target_loc = (profile.location or "").lower()
        if target_loc:
            parts = [p.strip() for p in target_loc.split(",")]
            if parts[0] in t_lower or parts[0] in s_lower:
                score += HEURISTIC_WEIGHTS.get("LOCATION_MATCH", 10)
            elif parts[-1] in (t_lower + s_lower):
                score += 5

        # 4. Industry / sector
        if profile.industry and profile.industry.lower() in (t_lower + " " + s_lower):
            score += HEURISTIC_WEIGHTS.get("INDUSTRY_MATCH", 5)
        elif profile.sector and profile.sector.lower() in (t_lower + " " + s_lower):
            score += HEURISTIC_WEIGHTS.get("INDUSTRY_MATCH", 5)

        # 5. Skills (word-boundary safe)
        user_skills = []
        if profile.user and profile.user.skills:
            for sk in profile.user.skills:
                name = sk.get("skill_name", "") if isinstance(sk, dict) else getattr(sk, "skill_name", "")
                if name:
                    user_skills.append(name.lower())
        text_for_skills = f" {t_lower} {s_lower} "
        if any(
            len(sk) > 2 and re.search(r"(?:\b|\s)" + re.escape(sk) + r"(?:\b|\s)", text_for_skills)
            for sk in user_skills
        ):
            score += HEURISTIC_WEIGHTS.get("SKILLS_MATCH", 15)

        # 6. Experience overlap
        if profile.user and profile.user.experiences:
            exp_words = set()
            for exp in profile.user.experiences:
                desc = exp.get("description", "") if isinstance(exp, dict) else getattr(exp, "description", "")
                if desc:
                    exp_words.update(w for w in desc.lower().split() if len(w) > 5)
            snippet_words = {w for w in s_lower.split() if len(w) > 5}
            if len(exp_words & snippet_words) >= 2:
                score += HEURISTIC_WEIGHTS.get("DESCRIPTION_MATCH", 20)

        # 7. Penalise junk
        if any(w in t_lower for w in ("cookie", "privacy", "headquarters",
                                       "about us", "our story", "leadership")):
            score -= 60

        return max(5, min(score, 98))

    def _detect_job_metadata(self, title: str, snippet: str) -> Dict[str, str]:
        text = f"{title} {snippet}".lower()

        level = "Mid-Senior Level"
        if any(w in text for w in ["intern", "praktik", "student", "trainee",
                                    "graduate", "entry", "junior"]):
            level = "Associate"
        elif any(w in text for w in ["executive", "chief", "c-level", "president",
                                      "ceo", "cto", "cfo", "coo"]):
            level = "Executive"
        elif any(w in text for w in ["director", "head of", "principal", "vp", "lead"]):
            level = "Director"

        mode = "Hybrid"
        if any(w in text for w in ["remote", "home office", "work from home",
                                    "telework", "anywhere"]):
            mode = "Remote"
        elif any(w in text for w in ["on-site", "in-office", "non-remote",
                                      "presence required"]):
            mode = "On-site"

        j_type = "Permanent"
        if any(w in text for w in ["contract", "freelance", "interim",
                                    "fixed-term", "cdd", "befristet"]):
            j_type = "Contract"

        return {"experience_level": level, "work_mode": mode, "job_type": j_type}

    def _detect_location(
        self, title: str, snippet: str, country: Optional[str] = None
    ) -> str:
        text = f"{title} {snippet}".lower()

        # Clear international signals
        intl = ["hyderabad", "bangalore", "bengaluru", "mumbai", "pune",
                "shanghai", "beijing", "tokyo", "hong kong", "singapore",
                "new york", "san francisco", "los angeles"]
        if any(b in text for b in intl) and country not in ("India", "Singapore", "USA"):
            return "International"

        cities = CITY_MAP.get(country, []) if country else []
        if not cities:
            for clist in CITY_MAP.values():
                cities.extend(clist)

        for city in cities:
            if city.lower() in text:
                return city

        return country or "Unknown"

    async def _verify_alignment_robust(
        self, content_md: str, profile: UserProfile
    ) -> Dict[str, Any]:
        """LLM deep-check: is this a single job that matches the user?"""
        if len(content_md) > 4000:
            content_md = content_md[:2000] + "\n...[TRUNCATED]...\n" + content_md[-2000:]

        prompt = f"""
Role: Senior Career Specialist.

Task: Deep alignment check between the [Job Page] and the [User Profile].

Rules:
1. PAGE TYPE — is this a SINGLE job description? Hard-fail if it is a list/search page.
2. LOCATION — is the job in {profile.location or 'Global'} or same country? Hard-fail only if completely different country.
3. SENIORITY — does it match {profile.desired_job_title}?
4. MATCH SCORE — integer 0-100.

Job Page:
{content_md}

User Profile:
- Target Role: {profile.desired_job_title}
- Summary: {(profile.summary or '')[:400]}

Return JSON ONLY:
{{
    "page_type": "single_job"|"aggregate_list"|"other",
    "match_score": 0-100,
    "extracted_title": "string",
    "extracted_company": "string",
    "reason": "one-line explanation"
}}
"""
        try:
            return await self.llm._get_gemini_response(prompt)
        except Exception as e:
            logger.error(f"LLM alignment check failed: {e}")
            return {"page_type": "other", "match_score": 0, "reason": str(e)}
