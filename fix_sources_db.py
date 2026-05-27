import sqlite3

conn = sqlite3.connect("career_revolution.db")
cur = conn.cursor()

fixes = 0
CORRECT_CH_GUID = "bead20140c8b4117b0795c65113c1c9c"

print("=== SPECIFIC URL FIXES ===")

# Roche id=6: URL already correct (facetCountry=CH) — just reactivate
cur.execute("UPDATE job_sources SET is_active=1, maturity_level='new', visual_validated=NULL WHERE id=6")
print(f"Roche id=6: reactivated (facetCountry=CH URL was already correct) [{cur.rowcount}]")

# ABB: Fix id=95 to use facetCountry=CH, deactivate all other ABB dupes
cur.execute("""
    UPDATE job_sources
    SET url='https://careers.abb/global/en/search-results?facetCountry=CH',
        is_active=1, maturity_level='new', visual_validated=NULL,
        name='ABB Careers Switzerland'
    WHERE id=95
""")
print(f"ABB id=95: fixed URL to facetCountry=CH [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%ABB%' AND id != 95")
print(f"ABB duplicates deactivated: {cur.rowcount}")

# UBS id=499: fix URL to add ?country=CH
cur.execute("""
    UPDATE job_sources
    SET url='https://www.ubs.com/global/en/careers/job-search.html?country=CH',
        is_active=1, maturity_level='new', visual_validated=NULL,
        name='UBS Careers Switzerland'
    WHERE id=499
""")
print(f"UBS id=499: fixed URL to ?country=CH [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%UBS%' AND id != 499")
print(f"UBS duplicates deactivated: {cur.rowcount}")

# Palantir id=124: fix URL to locations/zurich
cur.execute("""
    UPDATE job_sources
    SET url='https://www.palantir.com/careers/locations/zurich/',
        is_active=1, maturity_level='new', visual_validated=NULL,
        name='Palantir Zurich Careers'
    WHERE id=124
""")
print(f"Palantir id=124: fixed URL to /careers/locations/zurich/ [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%Palantir%' AND id != 124")
print(f"Palantir duplicates deactivated: {cur.rowcount}")

# Logitech id=395: remove unsupported ?l=Switzerland from Jobvite
cur.execute("""
    UPDATE job_sources
    SET url='https://jobs.jobvite.com/logitech/jobs',
        is_active=1, maturity_level='new', visual_validated=NULL,
        name='Logitech Careers'
    WHERE id=395
""")
print(f"Logitech id=395: removed ?l=Switzerland from Jobvite URL [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%Logitech%' AND id != 395")
print(f"Logitech duplicates deactivated: {cur.rowcount}")

# Lonza id=30: fix wrong Workday GUID
cur.execute(
    "UPDATE job_sources SET url=?, maturity_level='new', visual_validated=NULL WHERE id=30",
    (f"https://lonza.wd3.myworkdayjobs.com/Lonza_Careers?facetCountry={CORRECT_CH_GUID}",)
)
print(f"Lonza id=30: fixed Workday GUID to {CORRECT_CH_GUID} [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%Lonza%' AND id != 30 AND source_type='company_career_page'")
print(f"Lonza duplicates deactivated: {cur.rowcount}")

# Galderma id=366: fix wrong Workday GUID
cur.execute(
    "UPDATE job_sources SET url=?, maturity_level='new', visual_validated=NULL WHERE id=366",
    (f"https://galderma.wd3.myworkdayjobs.com/External?facetCountry={CORRECT_CH_GUID}",)
)
print(f"Galderma id=366: fixed Workday GUID to {CORRECT_CH_GUID} [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%Galderma%' AND id != 366")
print(f"Galderma duplicates deactivated: {cur.rowcount}")

# Zurich Insurance: reactivate the two best entries
cur.execute("""
    UPDATE job_sources
    SET is_active=1, maturity_level='new', visual_validated=NULL
    WHERE id IN (141, 198)
""")
print(f"Zurich Insurance id=141+198: reactivated [{cur.rowcount}]")
cur.execute("UPDATE job_sources SET is_active=0 WHERE name LIKE '%Zurich Insurance%' AND id NOT IN (141, 198)")
print(f"Zurich Insurance duplicates deactivated: {cur.rowcount}")

# Füllinsdorf-poisoned URLs — keep deactivated
cur.execute("UPDATE job_sources SET is_active=0 WHERE url LIKE '%llinsdorf%' OR url LIKE '%4414%'")
print(f"Poisoned (Füllinsdorf) URLs kept deactivated: {cur.rowcount}")

print("\n=== REACTIVATE VALID CAREER URLS THAT FAILED DUE TO BUGS ===")

# URLs that are clearly junk (wrong page type) — keep these deactivated
JUNK_URL_FRAGMENTS = [
    'general-terms', '/recycling/', '/stories/', '/news/', '/blog/',
    '/press/', '/investors/', '/products-services/', 'commitment-to-switzerland',
    'general-terms-and-conditions', 'lighthouse-for-sustainable', 'glass-recycling-',
]

CAREER_PATH_KW = (
    '/jobs', '/careers', '/career', '/vacancies', '/vacancy',
    '/offres', '/emploi', '/stellen', '/stelle', '/karriere',
    '/arbeit', '/work-with-us', '/join-us', '/open-positions',
    '/openings', '/recruitment', '/job-search', '/search',
    'myworkdayjobs', 'greenhouse.io', 'lever.co', 'successfactors',
    'icims.com', 'taleo.net', 'smartrecruiters', 'recruitee',
    'jobvite', 'jobs.', 'offene-stellen', 'job-openings',
    'locationsearch', 'job-vacancies',
)

# Find all inactive company_career_page sources with maturity=invalid
candidates = cur.execute("""
    SELECT id, name, url FROM job_sources
    WHERE is_active=0
      AND source_type='company_career_page'
      AND maturity_level='invalid'
""").fetchall()

to_reactivate = []
stay_dead = []
for row_id, name, url in candidates:
    url_lower = (url or '').lower()
    # Skip junk URLs
    if any(frag in url_lower for frag in JUNK_URL_FRAGMENTS):
        stay_dead.append((row_id, name, url))
        continue
    # Skip homepage-only URLs (no career path keyword)
    if not any(kw in url_lower for kw in CAREER_PATH_KW):
        stay_dead.append((row_id, name, url))
        continue
    to_reactivate.append(row_id)

if to_reactivate:
    placeholders = ','.join('?' * len(to_reactivate))
    cur.execute(
        f"UPDATE job_sources SET is_active=1, maturity_level='new', visual_validated=NULL WHERE id IN ({placeholders})",
        to_reactivate
    )
    print(f"Reactivated {cur.rowcount} sources with valid career URLs (reset to 'new')")

print(f"Kept deactivated (junk/homepage URLs): {len(stay_dead)}")
for row_id, name, url in stay_dead[:15]:
    print(f"  [id={row_id}] {name[:50]} - {url[:80]}")
if len(stay_dead) > 15:
    print(f"  ... and {len(stay_dead)-15} more")

conn.commit()

# Final summary
total_active = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1").fetchone()[0]
new_count = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='new'").fetchone()[0]
qualified_count = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='qualified'").fetchone()[0]
invalid_count = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=0").fetchone()[0]

print(f"\n=== FINAL STATE ===")
print(f"Total active: {total_active}")
print(f"  maturity=new  (queued for vetting): {new_count}")
print(f"  maturity=qualified (already good):  {qualified_count}")
print(f"Total inactive: {invalid_count}")

conn.close()
