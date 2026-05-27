"""
Quick DB inspection script to understand current state
before building the auto-apply test.
"""
import sqlite3

conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()

# Users
cur.execute('SELECT id, email, full_name FROM users')
users = cur.fetchall()
print('=== USERS ===')
for u in users:
    print(f'  id={u[0]}  email={u[1]}  name={u[2]}')

# Auto-apply credentials
try:
    cur.execute("""
        SELECT user_id, linkedin_url, linkedin_username, linkedin_password_enc,
               email_username, email_password_enc
        FROM auto_apply_credentials
    """)
    creds = cur.fetchall()
    print('\n=== AUTO-APPLY CREDENTIALS ===')
    for c in creds:
        print(f'  user_id={c[0]}  li_url={c[1]}  li_user={c[2]}  '
              f'li_pass_set={bool(c[3])}  email={c[4]}  email_pass_set={bool(c[5])}')
except Exception as e:
    print(f'  ERROR (table may not exist yet): {e}')

# Recent job applications
cur.execute("""
    SELECT id, user_id, status, application_url, job_opportunity_id, cv_path
    FROM job_applications
    ORDER BY id DESC
    LIMIT 5
""")
apps = cur.fetchall()
print('\n=== RECENT JOB APPLICATIONS ===')
for a in apps:
    url = (a[3] or '')[:70]
    print(f'  id={a[0]}  user={a[1]}  status={a[2]}  has_cv={bool(a[5])}  url={url}')

# LinkedIn jobs
cur.execute("""
    SELECT id, title, company, application_url
    FROM job_opportunities
    WHERE application_url LIKE '%linkedin%'
    LIMIT 5
""")
li_jobs = cur.fetchall()
print('\n=== LINKEDIN JOBS (sample) ===')
for j in li_jobs:
    print(f'  id={j[0]}  title={j[1]}  co={j[2]}  url={j[3][:80]}')

# Non-LinkedIn company portal jobs
cur.execute("""
    SELECT id, title, company, application_url
    FROM job_opportunities
    WHERE (application_url NOT LIKE '%linkedin%')
      AND application_url IS NOT NULL
      AND application_url != ''
    LIMIT 8
""")
other_jobs = cur.fetchall()
print('\n=== COMPANY PORTAL JOBS (non-LinkedIn) ===')
for j in other_jobs:
    print(f'  id={j[0]}  title={j[1]}  co={j[2]}  url={j[3][:80]}')

conn.close()
