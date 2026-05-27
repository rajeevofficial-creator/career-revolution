import sqlite3
conn = sqlite3.connect("career_revolution.db")
cur = conn.cursor()
total = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1").fetchone()[0]
new_c = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='new'").fetchone()[0]
qual = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='qualified'").fetchone()[0]
inactive = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=0").fetchone()[0]
print("Total active:", total)
print("  maturity=new (queued for vetting):", new_c)
print("  maturity=qualified (already good):", qual)
print("Total inactive:", inactive)

# Verify the specific fixes
checks = [
    (6,  "Roche",    "careers.roche.com/global/en/search-results?facetCountry=CH"),
    (95,  "ABB",     "careers.abb/global/en/search-results?facetCountry=CH"),
    (499, "UBS",     "job-search.html?country=CH"),
    (124, "Palantir","locations/zurich"),
    (395, "Logitech","jobs.jobvite.com/logitech/jobs"),
    (30,  "Lonza",   "bead20140c8b4117b0795c65113c1c9c"),
    (366, "Galderma","bead20140c8b4117b0795c65113c1c9c"),
]
print("\nKey source verification:")
for sid, label, expected_fragment in checks:
    row = cur.execute("SELECT name, url, is_active, maturity_level FROM job_sources WHERE id=?", (sid,)).fetchone()
    if row:
        ok = expected_fragment in row[1] and row[2] == 1
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {label} (id={sid}): active={row[2]} maturity={row[3]}")
        print(f"         url={row[1]}")
conn.close()
