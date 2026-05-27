import sqlite3
import os

db_path = "c:/Users/rajeev/career_revolution/career_revolution.db"

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns_to_add = [
    ("job_type", "VARCHAR(50)"),
    ("work_mode", "VARCHAR(50)"),
    ("experience_level", "VARCHAR(50)")
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE job_opportunities ADD COLUMN {col_name} {col_type}")
        print(f"Added column: {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"Column already exists: {col_name}")
        else:
            print(f"Error adding {col_name}: {e}")

conn.commit()
conn.close()
print("Migration complete.")
