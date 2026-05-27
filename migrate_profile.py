import sqlite3
import os

def migrate():
    db_path = "career_revolution.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("dob", "VARCHAR(50)"),
        ("nationality", "VARCHAR(100)"),
        ("marital_status", "VARCHAR(100)"),
        ("work_auth", "VARCHAR(100)")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to user_profiles")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists")
            else:
                print(f"Error adding {col_name}: {e}")
                
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
