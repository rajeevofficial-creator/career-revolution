import sqlite3
import os

for db_name in ["career_revolution.db", "app.db"]:
    db_path = os.path.join(r"c:\Users\rajeev\career_revolution", db_name)
    if os.path.exists(db_path):
        print(f"\n=== Database: {db_name} ===")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            print("Tables:", tables)
            
            if "users" in tables:
                cursor.execute("SELECT id, email, is_active FROM users")
                users = cursor.fetchall()
                print("Users:")
                for u in users:
                    print(f"  ID: {u[0]} | Email: {u[1]} | Active: {u[2]}")
                    
            if "job_applications" in tables:
                cursor.execute("SELECT id, user_id, job_opportunity_id, application_url, status FROM job_applications")
                apps = cursor.fetchall()
                print("Applications:")
                for app in apps:
                    print(f"  ID: {app[0]} | User ID: {app[1]} | Job ID: {app[2]} | URL: {app[3]} | Status: {app[4]}")
        except Exception as e:
            print("Error:", e)
        finally:
            conn.close()
    else:
        print(f"{db_name} does not exist")
