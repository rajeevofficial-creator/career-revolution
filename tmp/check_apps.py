"""
Check prepared applications and their linked job URLs for test target selection.
"""
import sqlite3

conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()

cur.execute("""
    SELECT ja.id, ja.status, ja.application_url, ja.cv_path, ja.cl_path,
           jo.title, jo.company, jo.application_url as job_url
    FROM job_applications ja
    LEFT JOIN job_opportunities jo ON ja.job_opportunity_id = jo.id
    WHERE ja.user_id = 1
    ORDER BY ja.id DESC
    LIMIT 10
""")
rows = cur.fetchall()
print('=== PREPARED APPLICATIONS WITH JOB URLs ===')
for r in rows:
    print(f'  app_id={r[0]}  status={r[1]}')
    print(f'    app_url  = {r[2]}')
    print(f'    job_url  = {r[7]}')
    print(f'    title    = {r[5]}  co={r[6]}')
    print(f'    cv_path  = {r[3]}')
    print()

# Also check auto_apply_accounts table
try:
    cur.execute("SELECT * FROM auto_apply_accounts WHERE user_id=1")
    accounts = cur.fetchall()
    print('=== AUTO-APPLY ACCOUNTS ===')
    for a in accounts:
        print(f'  {a}')
except Exception as e:
    print(f'auto_apply_accounts error: {e}')

conn.close()
