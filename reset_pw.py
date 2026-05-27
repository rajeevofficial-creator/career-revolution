import sqlite3
from app.services.auth import get_password_hash

h = get_password_hash('demo123')
print("New hash:", h)

conn = sqlite3.connect('career_revolution.db')
cur = conn.cursor()
cur.execute("UPDATE users SET password_hash = ? WHERE email = 'rajeev.sharma@mail.ch'", (h,))
conn.commit()
print("Updated rows:", cur.rowcount)
conn.close()
