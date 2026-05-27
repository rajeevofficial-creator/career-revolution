import sqlite3
conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()

total = cur.execute("SELECT COUNT(*) FROM job_opportunities").fetchone()[0]
empty = cur.execute("SELECT COUNT(*) FROM job_opportunities WHERE application_url IS NULL OR application_url = ''").fetchone()[0]
with_url = total - empty
print(f"Total: {total}, With URL: {with_url}, Empty URL: {empty}")
print()
print("Sample URLs:")
rows = cur.execute("SELECT title, company, application_url FROM job_opportunities WHERE application_url IS NOT NULL AND application_url != '' LIMIT 8").fetchall()
for r in rows:
    print(f"  [{r[1][:25]}] {r[0][:35]} -> {r[2][:65]}")
conn.close()
