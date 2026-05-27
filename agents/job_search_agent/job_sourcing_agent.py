"""
Job Sourcing Agent for Career Revolution.
Specially designed to find and maintain high-quality job portals, company pages, and recruiters.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.models.database import JobSource, User, UserProfile
from app.services.source_discovery import SourceDiscoveryService
from app.services.llm_analysis import LLMAnalysisService

logger = logging.getLogger(__name__)

class JobSourcingAgent:
    """Agent for discovering and maintaining job sources (portals, agencies, company pages)."""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMAnalysisService()
        self.discovery = SourceDiscoveryService(self.llm)
        
    async def run_sourcing_pipeline(self, user_id: int, country: str, force_update: bool = False) -> Dict[str, Any]:
        """
        Main entry point for sourcing:
        1. Require an explicit country (admin-selected from dropdown — never inferred from profile).
        2. Check if update is needed.
        3. Discover sources based on user profile industry and country.
        4. Update/Persist to DB.
        """
        if not country or not country.strip():
            return {"error": "country is required. Select a country from the dropdown before running sync."}

        country = country.strip()
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        industry = (profile.desired_industry or profile.industry or "General") if profile else "General"

        location = country

        # Check if we already have sources and when they were last checked
        existing_sources = self.db.query(JobSource).filter(
            JobSource.location_focus == location
        ).all()

        needs_update = force_update or not existing_sources

        if not needs_update:
            # Use NEWEST checked date — if anything was refreshed recently, sources are current
            checked_dates = [s.last_checked for s in existing_sources if s.last_checked]
            newest_check = max(checked_dates) if checked_dates else datetime.min
            if datetime.utcnow() - newest_check > timedelta(days=7):
                needs_update = True
                logger.info("Sources are older than 7 days. Refreshing...")
            else:
                logger.info("Sources are up to date (checked within the last 7 days).")
                return {
                    "status": "up_to_date",
                    "sources_count": len(existing_sources),
                    "last_checked": newest_check.isoformat()
                }

        # Step 0a: Clean existing sources BEFORE discovery
        # (removes duplicates and junk URLs so new sources are compared to a clean baseline)
        pre_clean = self._cleanup_sources(location)
        logger.info(f"Pre-discovery cleanup: {pre_clean}")

        # Step 0b: Import company career pages from CSV (country-filtered)
        from app.services.csv_import import CSVImportService
        csv_result = CSVImportService.import_companies(self.db, target_country=location)
        if "error" not in csv_result:
            logger.info(f"Imported {csv_result.get('new', 0)} companies from CSV for {location}.")

        # Step 1: Discover high-quality sources (AI Discovery)
        sources_data = await self.discovery.discover_sources(location, industry)
        
        new_count = 0
        updated_count = 0
        
        def normalize_name(name: str) -> str:
            """Normalise a source name for deduplication (lower, strip punctuation)."""
            import re
            return re.sub(r"[^a-z0-9]", "", name.lower().strip())[:40]

        # Deduplicate by normalised name+source_type — prevents LLM re-adding same source
        existing_sources = self.db.query(JobSource).all()
        name_map = {
            (normalize_name(s.name), s.source_type): s
            for s in existing_sources
        }

        for src in sources_data:
            url = src['url']
            # Truncate name to column length and strip any accidental description overflow
            src_name = src['name'][:200].split('.')[0].strip() if len(src['name']) > 200 else src['name']
            norm_key = (normalize_name(src_name), src.get('source_type', 'general'))

            existing = name_map.get(norm_key)
            
            # Map LLM metadata
            llm_industry = src.get('industry', industry)
            llm_sector = src.get('sector', '')
            
            # Refine tags: Mix of portal type and company attributes
            src_tags = src.get('tags', [])
            if llm_sector and llm_sector not in src_tags: src_tags.append(llm_sector)
            if llm_industry and llm_industry not in src_tags: src_tags.append(llm_industry)
            tags_json = json.dumps(list(set(src_tags)))
            
            if not existing:
                new_src = JobSource(
                    name=src['name'],
                    url=url,
                    source_type=src['source_type'],
                    industry=llm_industry,
                    sector=llm_sector,
                    industry_focus=llm_industry,
                    location_focus=location,
                    country=location,
                    quality_score=src.get('quality_score', 50),
                    description=src.get('reasoning', ''),
                    tags=tags_json,
                    is_active=True,
                    last_checked=datetime.utcnow()
                )
                self.db.add(new_src)
                self.db.flush()
                new_count += 1
            else:
                # Update existing source metadata
                existing.country = country
                if not existing.industry or existing.industry_focus == "IT":
                    existing.industry = llm_industry
                    existing.sector = llm_sector or existing.sector
                    existing.industry_focus = llm_industry

                existing.name = src['name']
                existing.quality_score = src.get('quality_score', existing.quality_score)
                existing.description = src.get('reasoning', existing.description)
                existing.tags = tags_json
                existing.last_checked = datetime.utcnow()

                # Update URL if the new one is more specific (has a longer path with job-related keywords)
                from urllib.parse import urlparse as _up
                new_path = _up(url).path.lower()
                old_path = _up(existing.url).path.lower()
                job_kw = ("/jobs", "/careers", "/vacancies", "/search", "/offres", "/stellen", "facetcountry", "geoid")
                new_is_specific = any(k in new_path or k in url.lower() for k in job_kw)
                old_is_specific = any(k in old_path or k in existing.url.lower() for k in job_kw)
                if new_is_specific and not old_is_specific:
                    existing.url = url

                updated_count += 1
                
        self.db.commit()
        
        # Vet sources: force=True re-vets all active sources, force=False only new ones
        vet_result = await self.vet_all_sources(country=location, force=force_update)

        # Post-vet cleanup: deactivate sources that failed visual validation
        post_clean = self._cleanup_sources(location, post_vet=True)
        logger.info(f"Post-vet cleanup: {post_clean}")

        csv_new = csv_result.get("new", 0)
        total_active = self.db.query(JobSource).filter(JobSource.is_active == True).count()

        return {
            "status": "refreshed",
            "new_sources": new_count + csv_new,
            "updated_sources": updated_count,
            "vetted_count": vet_result.get("updated", 0),
            "visually_valid": vet_result.get("visually_valid", 0),
            "visually_invalid": vet_result.get("visually_invalid", 0),
            "visually_skipped": vet_result.get("visually_skipped", 0),
            "deduped": pre_clean.get("url_dupes_removed", 0),
            "deactivated_invalid": post_clean.get("invalid_deactivated", 0),
            "total_active_sources": total_active,
        }

    async def vet_all_sources(self, country: str = None, force: bool = False) -> Dict[str, Any]:
        """
        Refine URLs and visually validate active sources.

        force=False (default): only process sources with maturity_level='new'
        force=True:  re-run URL refinement on ALL active sources; re-run visual
                     validation only on company_career_pages that have never been
                     validated (visual_validated IS NULL) or previously failed.
        """
        from app.models.database import SessionLocal

        q = self.db.query(JobSource).filter(JobSource.is_active == True)
        if not force:
            q = q.filter(JobSource.maturity_level == 'new')
        sources = q.all()

        if not sources:
            return {"status": "no_sources_to_vet", "total_processed": 0, "updated": 0}

        updated_count = 0
        source_ids = [s.id for s in sources]
        logger.info(f"Vetting {len(source_ids)} sources (force={force}, country={country})...")

        semaphore = asyncio.Semaphore(5)

        visually_valid = 0
        visually_invalid = 0
        visually_skipped = 0

        async def vet_one(source_id):
            nonlocal updated_count, visually_valid, visually_invalid, visually_skipped
            async with semaphore:
                local_db = SessionLocal()
                try:
                    source = local_db.query(JobSource).filter(JobSource.id == source_id).first()
                    if not source: return

                    vet_country = country or source.country or source.location_focus

                    # Phase 0 (CSV-imported companies): no URL stored yet — discover via name
                    if not source.url:
                        discovered = await self.discovery.discover_career_url_by_name(
                            source.name, vet_country
                        )
                        if discovered:
                            source.url = discovered
                            source.visual_validated = None
                            logger.info(f"Discovered URL for '{source.name}': {discovered}")
                        else:
                            logger.warning(f"Could not discover career URL for '{source.name}' — skipping")
                            source.maturity_level = "invalid"
                            local_db.commit()
                            return

                    # Phase 1-3: URL refinement (HTML scrape → LLM → HTTP verify)
                    # Always run — fast HTTP-based, fixes stale/wrong URLs
                    vetted_url = await self.discovery.vet_company_url(source.url, country=vet_country)
                    if vetted_url and vetted_url != source.url:
                        logger.info(f"Refined {source.name}: {source.url} -> {vetted_url}")
                        source.url = vetted_url
                        # URL changed — clear previous validation so it gets re-checked below
                        source.visual_validated = None

                    # Phase 4: Visual validation — Playwright screenshot + Gemini Vision
                    # Only for company_career_page (portals/recruiters trusted via URL check).
                    # Skip if already confirmed valid AND URL didn't change this run.
                    if source.source_type == "company_career_page":
                        needs_visual = (
                            source.visual_validated is None        # never validated
                            or source.visual_validated is False    # previously failed
                        )
                        if not needs_visual:
                            # Already confirmed good and URL unchanged — skip Playwright
                            source.maturity_level = "qualified"
                            visually_skipped += 1
                        else:
                            vision_result = await self.discovery.visual_validate_source(
                                source.url, country=vet_country
                            )
                            source.visual_validated = vision_result.get("valid")
                            source.validation_notes = (
                                f"[{vision_result.get('confidence','?')}] "
                                f"{vision_result.get('notes', '')} "
                                f"| ~{vision_result.get('job_count', '?')} jobs visible "
                                f"| country_specific={vision_result.get('country_ok', '?')}"
                            )
                            if vision_result.get("valid") is False:
                                source.maturity_level = "invalid"
                                visually_invalid += 1
                                logger.warning(
                                    f"Visual validation FAILED for {source.name} ({source.url}): "
                                    f"{vision_result.get('notes')}"
                                )
                            elif vision_result.get("valid") is True:
                                source.maturity_level = "qualified"
                                visually_valid += 1
                            else:
                                # Vision unavailable — mark qualified so we don't endlessly re-vet
                                source.maturity_level = "qualified"
                    else:
                        # Portals / recruiters: URL verification alone is sufficient
                        source.maturity_level = "qualified"

                    local_db.commit()
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to vet source {source_id}: {e}")
                    local_db.rollback()
                finally:
                    local_db.close()

        tasks = [vet_one(sid) for sid in source_ids]
        await asyncio.gather(*tasks)

        return {
            "total_processed": len(source_ids),
            "updated": updated_count,
            "visually_valid": visually_valid,
            "visually_invalid": visually_invalid,
            "visually_skipped": visually_skipped,
            "status": "completed"
        }

    def _cleanup_sources(self, country: str, post_vet: bool = False) -> Dict[str, Any]:
        """
        pre-vet (post_vet=False): deduplicate by URL, deactivate junk/redirect URLs
        post-vet (post_vet=True): deactivate sources with maturity_level='invalid'
        """
        import re
        from urllib.parse import urlparse

        url_dupes_removed = 0
        junk_deactivated = 0
        invalid_deactivated = 0

        # Junk URL patterns: login redirects, error pages, generic homepages with no path
        JUNK_URL_PATTERNS = [
            r"accounts\.google\.com",
            r"login\.",
            r"/login",
            r"/signin",
            r"/sign-in",
            r"ServiceLogin",
            r"oauth",
            r"/auth/",
            r"accounts\.",
            r"sso\.",
        ]
        junk_re = re.compile("|".join(JUNK_URL_PATTERNS), re.IGNORECASE)

        if post_vet:
            # Deactivate sources that failed visual validation
            invalid_sources = (
                self.db.query(JobSource)
                .filter(
                    JobSource.is_active == True,
                    JobSource.maturity_level == "invalid",
                )
                .all()
            )
            for src in invalid_sources:
                src.is_active = False
                invalid_deactivated += 1
                logger.info(f"Deactivated invalid source: {src.name} ({src.url})")
            self.db.commit()
        else:
            # --- Step 1: Deactivate junk/redirect URLs ---
            active_sources = self.db.query(JobSource).filter(JobSource.is_active == True).all()
            for src in active_sources:
                if junk_re.search(src.url or ""):
                    src.is_active = False
                    junk_deactivated += 1
                    logger.info(f"Deactivated junk URL: {src.name} ({src.url})")
            self.db.commit()

            # --- Step 2: Deduplicate by normalised URL ---
            # Reload after deactivation
            active_sources = self.db.query(JobSource).filter(JobSource.is_active == True).all()

            def _norm_url(url: str) -> str:
                """Lowercase, strip trailing slash, drop query/fragment for dedup key."""
                try:
                    p = urlparse(url.lower().strip())
                    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}"
                except Exception:
                    return url.lower().strip()

            url_groups: Dict[str, list] = {}
            for src in active_sources:
                key = _norm_url(src.url or "")
                url_groups.setdefault(key, []).append(src)

            for key, group in url_groups.items():
                if len(group) <= 1:
                    continue
                # Keep the one with highest quality_score; tie-break by lowest id (oldest)
                group.sort(key=lambda s: (-( s.quality_score or 0), s.id))
                keeper = group[0]
                for dup in group[1:]:
                    dup.is_active = False
                    url_dupes_removed += 1
                    logger.info(
                        f"Deduped URL '{key}': keeping '{keeper.name}' (id={keeper.id}), "
                        f"deactivating '{dup.name}' (id={dup.id})"
                    )
            self.db.commit()

        return {
            "url_dupes_removed": url_dupes_removed,
            "junk_deactivated": junk_deactivated,
            "invalid_deactivated": invalid_deactivated,
        }
