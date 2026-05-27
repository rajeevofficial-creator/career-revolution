import sqlite3

def reset():
    conn = sqlite3.connect('career_revolution.db')
    cursor = conn.cursor()
    
    # Reset all to 'new' so we can do a fresh vetting pass with the fixed JSON logic
    cursor.execute("UPDATE job_sources SET maturity_level = 'new'")
    print(f"Reset {conn.total_changes} sources to 'new'.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset()
