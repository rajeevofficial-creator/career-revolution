import sqlite3

db_path = r"c:\Users\rajeev\career_revolution\career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, user_id, job_opportunity_id, application_url, status, notes FROM job_applications")
apps = cursor.fetchall()
print("--- ALL APPLICATIONS ---")
for app in apps:
    print(app)

cursor.execute("SELECT id, title, company, application_url FROM job_opportunities ORDER BY id DESC LIMIT 20")
jobs = cursor.fetchall()
print("\n--- LAST 20 JOBS ---")
for job in jobs:
    print(job)

conn.close()
