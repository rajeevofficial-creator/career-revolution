import sqlite3, json

conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()

# Check actual columns in job_applications
cur.execute("PRAGMA table_info(job_applications)")
cols_info = cur.fetchall()
print("=== job_applications columns ===")
for c in cols_info:
    print(f"  {c[1]} ({c[2]})")

# Full record for Valora app (id=8)
col_names = [c[1] for c in cols_info]
cur.execute("SELECT * FROM job_applications WHERE id = 8")
row = cur.fetchone()
print("\n=== APPLICATION ID=8 (Valora) ===")
if row:
    for col, val in zip(col_names, row):
        if val is not None and val != '':
            print(f"  {col:35s}: {val}")

# All applied
print("\n=== ALL APPLIED APPLICATIONS ===")
cur.execute("SELECT id, status, application_url FROM job_applications WHERE status='applied'")
for r in cur.fetchall():
    print(f"  id={r[0]}  url={r[2]}")

conn.close()
