
import sqlite3
conn = sqlite3.connect('career_revolution.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(job_applications)")
for col in cursor.fetchall():
    print(col[1])
conn.close()
