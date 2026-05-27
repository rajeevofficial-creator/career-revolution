import sqlite3

db_path = r"c:\Users\rajeev\career_revolution\career_revolution.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, title, company, description IS NULL FROM job_opportunities WHERE id IN (797, 798)")
jobs = cursor.fetchall()
for job in jobs:
    print(f"Job ID: {job[0]} | Title: {job[1]} | Company: {job[2]} | Desc Is Null: {job[3]}")

conn.close()
