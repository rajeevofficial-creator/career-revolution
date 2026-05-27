import sqlite3

db_path = r"c:\Users\rajeev\career_revolution\career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get job applications
cursor.execute("SELECT id, job_opportunity_id, application_url, status, tailored_cv IS NOT NULL FROM job_applications")
apps = cursor.fetchall()
print("--- Job Applications ---")
for app in apps:
    app_id, job_id, url, status, has_cv = app
    print(f"App ID: {app_id} | Job ID: {job_id} | URL: {url} | Status: {status} | Has CV: {has_cv}")

# Get job opportunities
cursor.execute("SELECT id, title, company, application_url, LENGTH(description), description IS NULL FROM job_opportunities ORDER BY id DESC LIMIT 10")
jobs = cursor.fetchall()
print("\n--- Job Opportunities (Last 10) ---")
for job in jobs:
    jid, title, company, url, desc_len, is_null = job
    print(f"Job ID: {jid} | Title: {title} | Company: {company} | URL: {url} | Desc Length: {desc_len} | Is Null: {is_null}")

conn.close()
