
import sqlite3
import json

conn = sqlite3.connect('career_revolution.db')
cursor = conn.cursor()

# Get the last application log
cursor.execute("SELECT id, auto_apply_log, status, intervention_message FROM job_applications ORDER BY id DESC LIMIT 1")
row = cursor.fetchone()

if row:
    app_id, log_json, status, msg = row
    print(f"App ID: {app_id}")
    print(f"Status: {status}")
    print(f"Message: {msg}")
    print("Full Log:")
    log = json.loads(log_json or "[]")
    for line in log:
        print(f"  > {line}")
else:
    print("No applications found.")

conn.close()
