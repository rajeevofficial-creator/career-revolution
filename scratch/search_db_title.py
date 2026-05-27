import sqlite3

db_path = r"c:\Users\rajeev\career_revolution\career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, title, company, application_url FROM job_opportunities WHERE title LIKE '%Job Title%' OR company LIKE '%Company%'")
res = cursor.fetchall()
print("Matches in career_revolution.db:")
for r in res:
    print(r)

conn.close()
