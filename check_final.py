import sqlite3
conn = sqlite3.connect("career_revolution.db")
cur = conn.cursor()

print("=== FINAL SYNC STATE ===")
total = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1").fetchone()[0]
new_c = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='new'").fetchone()[0]
qual = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND maturity_level='qualified'").fetchone()[0]
inactive = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=0").fetchone()[0]
vis_ok = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND visual_validated=1").fetchone()[0]
vis_skip = cur.execute("SELECT COUNT(*) FROM job_sources WHERE is_active=1 AND visual_validated IS NULL").fetchone()[0]

print(f"Total active: {total}")
print(f"  qualified: {qual}")
print(f"  visually confirmed valid: {vis_ok}")
print(f"  visual skipped (portals/recruiters): {vis_skip}")
print(f"Total inactive: {inactive}")

print("\n--- Active by source_type ---")
rows = cur.execute("""
    SELECT source_type, COUNT(*), SUM(CASE WHEN visual_validated=1 THEN 1 ELSE 0 END) as vis_ok
    FROM job_sources WHERE is_active=1 GROUP BY source_type ORDER BY COUNT(*) DESC
""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} total, {r[2]} visually confirmed")

print("\n--- Visually confirmed company career pages ---")
rows = cur.execute("""
    SELECT name, url FROM job_sources
    WHERE is_active=1 AND source_type='company_career_page' AND visual_validated=1
    ORDER BY name LIMIT 30
""").fetchall()
for r in rows:
    print(f"  OK  {r[0][:45]:<45} {r[1][:65]}")

print("\n--- Issues: empty URL (CSV companies that couldn't be discovered) ---")
rows = cur.execute("""
    SELECT name, maturity_level FROM job_sources
    WHERE url='' OR url IS NULL ORDER BY name LIMIT 20
""").fetchall()
for r in rows:
    print(f"  [{r[1]}] {r[0][:80]}")

print("\n--- Dedup issue: our facetCountry fixes vs what was kept ---")
for name_like, our_id in [("ABB%", 95), ("Roche%", 6), ("UBS%", 499), ("Logitech%", 395)]:
    print(f"\n  {name_like}:")
    rows = cur.execute("""
        SELECT id, name, url, is_active, maturity_level
        FROM job_sources WHERE name LIKE ? ORDER BY is_active DESC, id
    """, (name_like,)).fetchall()
    for r in rows:
        marker = "<-- OUR FIX" if r[0] == our_id else ""
        print(f"    [id={r[0]} active={r[3]} {r[4]}] {r[1][:35]} -> {(r[2] or 'NO URL')[:60]} {marker}")

conn.close()
