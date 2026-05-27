
import sqlite3
import json

conn = sqlite3.connect('career_revolution.db')
cursor = conn.cursor()

cursor.execute("SELECT id, status, intervention_message, auto_apply_log FROM job_applications ORDER BY id DESC LIMIT 5;")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Status: {row[1]}")
    print(f"Intervention: {row[2]}")
    print("Log:")
    try:
        log_data = json.loads(row[3])
        for line in log_data:
            print(f"  {line}")
    except:
        print(f"  {row[3]}")
    print("-" * 40)

conn.close()
