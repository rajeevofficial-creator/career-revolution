# Sync & Refine Sources — Issues Backlog

Issues identified from the sync run on 2026-04-28. To be fixed before the next full
re-sync. Job Finder (Refresh Jobs) is being tested first to confirm the current
vetted list is good enough to work with.

---

## P1 — Logic Bugs

### 1. Dedup loses country-filtered URLs
**File**: `agents/job_search_agent/job_sourcing_agent.py` → `_cleanup_sources`
**Problem**: `_norm_url()` strips query params before dedup comparison. So
`careers.abb?facetCountry=CH` and `careers.abb?location=Switzerland` map to the
same key. The sort picks the lowest ID (oldest entry) which never has the CH filter.
Our manually fixed ABB, Roche, UBS, Logitech entries were all deactivated.
**Fix**: In the dedup sort, add a tiebreaker that prefers URLs containing
country-specific params (`facetCountry`, `locationsearch`, `country=CH`, `geoid`).

### 2. `vet_company_url` downgrades specific URLs
**File**: `app/services/source_discovery.py` → `vet_company_url`
**Problem**: Phase 2 (LLM) sometimes returns the base URL without country filter when
the input already has `?facetCountry=CH`. Since base URL HTTP-verifies, it replaces
the more specific one. Logitech: `logitech.wd5.myworkdayjobs.com/logitech?facetCountry=CH`
got downgraded to base Workday URL without the filter.
**Fix**: Before accepting the LLM URL, check that it doesn't *remove* country-specific
params that the current URL already has. If it does, keep the current URL.

### 3. Long CSV descriptions used as company names
**File**: `app/services/csv_import.py`
**Problem**: The `description` field in the stock CSV is a full company profile paragraph
("Baloise Holding AG, together with its subsidiaries, primarily engages in...").
`discover_career_url_by_name` receives the whole paragraph as the "company name" — LLM
can't reliably find a career URL for a paragraph. 8 companies ended up with empty URLs
(Baloise, Basler Kantonalbank, Bell Food, Lonza-CSV, Novartis, Swisscom, UBS-CSV,
Zurich Insurance-CSV).
**Fix**: In `csv_import.py`, extract company name as text before first comma, or before
keywords like "together with", "provides", "operates", "engages in".

---

## P2 — Infrastructure / Process

### 4. force_update=True re-vets everything — wasteful
**Problem**: Running sync with `force=True` re-runs Playwright visual validation on all
360 sources, including already-qualified ones. One full run takes ~75 minutes.
**Design intent**: `force=False` (default) only vets sources with `maturity_level='new'`.
The vetted list should be preserved and incremental sync should only process new entries.
**Action**: Never use `force=True` in production. Reserve it only for a deliberate
"re-validate everything" admin action. Document this clearly.

### 5. CSV source — stock portfolio list is not authoritative
**Problem**: The current `stock_profile.csv` is from a personal stock application —
not a canonical list of Swiss employers.
**Better source**: SIX Swiss Exchange (six-group.com) publishes the official SMI/SPI
constituent lists. The SPI (Swiss Performance Index) covers ~200 Swiss companies.
Options:
- SIX Exchange Regulation API or data downloads (check six-group.com/exchanges/shares)
- `swissindex.ch` or `six-group.com` data feeds
- As fallback: Wikipedia SMI constituent list is maintained and linkable
**Action**: Evaluate SIX data availability before next sync prep. If available,
replace the CSV with an SIX-sourced company list for the canonical Swiss employer set.

---

## P3 — Environment / Testing Artefacts (Not real production issues)

### 6. Geo-blocked sites (Swisscom, etc.)
**Status**: NOT a real issue in production.
The visual validation ran from the development machine (outside Switzerland).
Sites like Swisscom detect non-Swiss IPs and show a geo-block page.
When the application runs from a Swiss IP (user's machine or Swiss-hosted server),
these pages will render normally. No code change needed — this was a test environment
artefact.

---

## Already Fixed (this session)
- Country auto-detection from profile (Füllinsdorf bug) → country now admin-selected
- CSV blindly using web URLs → name-only import + LLM discovers career URL
- `_scrape_for_country_url` returning T&C/news/job-posting URLs
- `_llm_suggest_country_url` guessing wrong Workday GUIDs / unsupported params
- `visual_validate_source` bot-detection, cookie banners, scroll, API error handling
- `validate_job_page_image` returning False on inconclusive API responses
- `_cleanup_sources` method missing entirely
- `/jobs/sources/countries` dropdown endpoint added
- `/jobs/sources/run` country parameter now required
