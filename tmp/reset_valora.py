import sqlite3
import json
import os

def reset_valora_application():
    db_path = 'career_revolution.db'
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Identify columns for safer update
        cur.execute('PRAGMA table_info(job_applications)')
        cols = [c[1] for c in cur.fetchall()]
        print(f"Found columns: {cols}")

        update_parts = ["status = 'prepared'", "applied_at = NULL"]
        
        # Check for auto_apply_log vs notes
        if 'auto_apply_log' in cols:
            update_parts.append("auto_apply_log = '[]'")
        if 'intervention_message' in cols:
            update_parts.append("intervention_message = NULL")
        if 'notes' in cols:
            update_parts.append("notes = ''")

        sql = f"UPDATE job_applications SET {', '.join(update_parts)} WHERE id = 8"
        print(f"Executing: {sql}")
        
        cur.execute(sql)
        conn.commit()
        
        if cur.rowcount > 0:
            print(f"Successfully reset application ID 8 (Valora). Rows updated: {cur.rowcount}")
        else:
            print("Warning: Application ID 8 not found in database.")

        conn.close()
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_valora_application()
