
import sqlite3
import os

db_path = r'c:\Users\rajeev\career_revolution\career_revolution.db'

def cleanup():
    if not os.path.exists(db_path):
        print(f"Error: DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    junk_titles = [
        'Inhalt', 'Job Title Sort ascending', 'This Month', 
        'Last Two Weeks', 'Last 24h', 'Search for', 
        'View all', 'Anytime', 'Summary', 'Job search',
        'Learn More', 'Navigation', 'Sort by'
    ]
    
    placeholders = ",".join(["?"] * len(junk_titles))
    
    # Delete from job_matches first
    cur.execute(f"DELETE FROM job_matches WHERE job_opportunity_id IN (SELECT id FROM job_opportunities WHERE title IN ({placeholders}))", junk_titles)
    matches_removed = cur.rowcount
    
    # Delete from job_opportunities
    cur.execute(f"DELETE FROM job_opportunities WHERE title IN ({placeholders})", junk_titles)
    opps_removed = cur.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Cleanup Complete:")
    print(f" - Matches removed: {matches_removed}")
    print(f" - Opportunities removed: {opps_removed}")

if __name__ == "__main__":
    cleanup()
