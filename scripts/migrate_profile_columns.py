import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'career_revolution.db')

def migrate():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(user_profiles)")
    columns = [col[1] for col in cursor.fetchall()]
    
    changes_made = False
    
    if 'sector' not in columns:
        print("Adding 'sector' column to user_profiles table...")
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN sector TEXT NULL")
        changes_made = True
        
    if 'industry' not in columns:
        print("Adding 'industry' column to user_profiles table...")
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN industry TEXT NULL")
        changes_made = True
        
    if changes_made:
        conn.commit()
        print("Migration completed successfully.")
    else:
        print("Columns already exist. No migration needed.")
        
    conn.close()

if __name__ == '__main__':
    migrate()
