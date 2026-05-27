import sqlite3
import os

db_path = "career_revolution.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Adding 'sector' and 'industry' columns to 'job_sources' table...")
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(job_sources)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "sector" not in columns:
        cursor.execute("ALTER TABLE job_sources ADD COLUMN sector VARCHAR(255)")
        print("Added 'sector' column.")
    else:
        print("'sector' column already exists.")
        
    if "industry" not in columns:
        cursor.execute("ALTER TABLE job_sources ADD COLUMN industry VARCHAR(255)")
        print("Added 'industry' column.")
    else:
        print("'industry' column already exists.")
        
    conn.commit()
    conn.close()
    print("Schema update completed successfully.")
except Exception as e:
    print(f"Error updating schema: {e}")
    exit(1)
