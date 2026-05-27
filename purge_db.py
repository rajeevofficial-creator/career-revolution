import sqlite3

def purge():
    conn = sqlite3.connect('career_revolution.db')
    cursor = conn.cursor()
    
    # Tables to purge
    tables = ['job_sources', 'job_opportunities', 'job_applications']
    
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Purged {cursor.rowcount} records from {table}.")
        except Exception as e:
            print(f"Error purging {table}: {e}")
            
    conn.commit()
    conn.close()
    print("Database purge complete.")

if __name__ == "__main__":
    purge()
