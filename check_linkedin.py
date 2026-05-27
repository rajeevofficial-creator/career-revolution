import sqlite3
conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()

print("=== LinkedIn sources in DB ===")
rows = cur.execute("""SELECT id, name, url, is_active, maturity_level, source_type
    FROM job_sources WHERE name LIKE '%LinkedIn%' OR url LIKE '%linkedin%'""").fetchall()
for r in rows:
    print(f"  [id={r[0]} active={r[3]} {r[4]}] {r[1][:40]} -> {r[2][:60]}")

print()
print("=== Jobs attributed to LinkedIn source ===")
rows = cur.execute("""SELECT jo.title, jo.company, jo.application_url
    FROM job_opportunities jo
    JOIN job_sources js ON jo.source_id = js.id
    WHERE js.name LIKE '%LinkedIn%' OR js.url LIKE '%linkedin%'
    LIMIT 10""").fetchall()
if rows:
    for r in rows:
        print(f"  {r[1][:25]}: {r[0][:45]} -> {r[2][:55]}")
else:
    print("  No jobs attributed to LinkedIn source")

print()
print("=== Jobs with linkedin.com in URL ===")
cnt = cur.execute("SELECT COUNT(*) FROM job_opportunities WHERE application_url LIKE '%linkedin%'").fetchone()[0]
print(f"  Count: {cnt}")
if cnt > 0:
    rows = cur.execute("SELECT title, company, application_url FROM job_opportunities WHERE application_url LIKE '%linkedin%' LIMIT 5").fetchall()
    for r in rows:
        print(f"  {r[1][:25]}: {r[0][:40]} -> {r[2][:60]}")

print()
print("=== What the LinkedIn source actually returned in last refresh ===")
rows = cur.execute("""SELECT js.name, COUNT(jo.id) as cnt
    FROM job_sources js
    LEFT JOIN job_opportunities jo ON jo.source_id = js.id
    WHERE js.name LIKE '%LinkedIn%' OR js.url LIKE '%linkedin%'
    GROUP BY js.id, js.name""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} jobs in DB")

conn.close()
