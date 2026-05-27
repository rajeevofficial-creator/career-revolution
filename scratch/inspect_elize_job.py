import sqlite3

db_path = r"c:\Users\rajeev\career_revolution\career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, title, company, application_url, description FROM job_opportunities WHERE company LIKE '%Elize%' OR title LIKE '%Senior Project Manager%'")
res = cursor.fetchall()
print("Matches in job_opportunities:")
for r in res:
    print(f"ID: {r[0]} | Title: {r[1]} | Company: {r[2]} | URL: {r[3]} | Has Desc: {r[4] is not None and len(r[4]) > 0}")

cursor.execute("SELECT id, user_id, job_opportunity_id, status FROM job_applications WHERE job_opportunity_id IN (SELECT id FROM job_opportunities WHERE company LIKE '%Elize%' OR title LIKE '%Senior Project Manager%')")
res_apps = cursor.fetchall()
print("\nMatches in job_applications:")
for r in res_apps:
    print(f"App ID: {r[0]} | User ID: {r[1]} | Job ID: {r[2]} | Status: {r[3]}")

conn.close()
