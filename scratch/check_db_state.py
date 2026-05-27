import sqlite3
import os

db_path = "career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- users ---")
cursor.execute("SELECT id, email, full_name FROM users")
for row in cursor.fetchall():
    print(row)

print("\n--- linkedin_sessions ---")
cursor.execute("SELECT user_id, is_valid, last_login_at, last_fetch_at, profile_name FROM linkedin_sessions")
for row in cursor.fetchall():
    print(row)

print("\n--- job_applications (recent) ---")
cursor.execute("SELECT id, user_id, job_opportunity_id, application_url, status FROM job_applications ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()
