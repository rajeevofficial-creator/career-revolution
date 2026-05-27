import csv
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.database import JobSource

logger = logging.getLogger(__name__)

def _resolve_csv_path(csv_path: str = None) -> str | None:
    """Resolve the CSV path: explicit arg → project data/ dir → Desktop fallback."""
    if csv_path and os.path.exists(csv_path):
        return csv_path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    local_path = os.path.join(project_root, "data", "stock_profile.csv")
    if os.path.exists(local_path):
        return local_path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "stock_profile.csv")
    if os.path.exists(desktop_path):
        return desktop_path
    return None


class CSVImportService:
    @staticmethod
    def import_companies(db: Session, target_country: str = "Switzerland", csv_path: str = None) -> Dict[str, Any]:
        """
        Import company names from the CSV as candidate sources.

        Only company name, country, industry and sector are taken from the CSV.
        No URL is stored — the vetting pipeline will call the LLM to discover the
        correct career/jobs page URL for each company.
        """
        resolved_path = _resolve_csv_path(csv_path)
        if not resolved_path:
            logger.warning("stock_profile.csv not found in data/ or Desktop — skipping CSV import.")
            return {"new": 0, "skipped": 0, "warning": "CSV not found"}

        new_count = 0
        skipped_count = 0
        country_filter = target_country.lower()

        try:
            with open(resolved_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Filter for the requested country only
                    country = row.get('country', '').strip()
                    if country.lower() != country_filter:
                        continue

                    name = row.get('description', row.get('name', '')).strip()
                    if not name:
                        continue

                    # Truncate long description fields to a clean company name
                    # (CSV descriptions can be multi-sentence company profiles)
                    if len(name) > 200:
                        name = name[:200].split('.')[0].strip()

                    industry = row.get('industry', '').strip()
                    sector = row.get('sector', '').strip()

                    # Deduplicate by normalised company name — URL-based dedup is not
                    # applicable here since we intentionally store no URL at import time.
                    norm_name = name.lower().strip()[:100]
                    existing = db.query(JobSource).filter(
                        JobSource.name.ilike(f"%{norm_name[:60]}%"),
                        JobSource.source_type == 'company_career_page',
                        JobSource.country == target_country,
                    ).first()

                    tags = [target_country]
                    if sector:
                        tags.append(sector)
                    if industry:
                        tags.append(industry)

                    if not existing:
                        source = JobSource(
                            name=name,
                            # URL intentionally blank — the vetting step (vet_all_sources)
                            # will call discover_career_url_by_name() to find the real URL.
                            url='',
                            source_type='company_career_page',
                            industry_focus=industry or "General",
                            location_focus=target_country,
                            country=target_country,
                            maturity_level='new',
                            industry=industry,
                            sector=sector,
                            is_active=True,
                            last_checked=datetime.utcnow(),
                            description=f"Imported from stock profile. Sector: {sector}",
                            tags=json.dumps(tags)
                        )
                        db.add(source)
                        new_count += 1
                    else:
                        # Enrich metadata if it was previously unknown
                        if not existing.industry or existing.industry_focus == "IT":
                            existing.industry = industry or existing.industry
                            existing.sector = sector or existing.sector
                            existing.industry_focus = industry or existing.industry_focus
                            existing.tags = json.dumps(
                                list(set(json.loads(existing.tags or "[]") + tags))
                            )
                        skipped_count += 1

                db.commit()
                logger.info(
                    f"CSV import complete: {new_count} new, {skipped_count} skipped "
                    f"(country={target_country}). No URLs stored — vetting will discover them."
                )
                return {"new": new_count, "skipped": skipped_count}
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            return {"error": str(e)}
