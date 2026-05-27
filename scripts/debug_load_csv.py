import sys
import os
import csv
import sqlite3

# Add the project root to sys.path
sys.path.append(os.getcwd())

from scripts.enrich_job_sources_v4 import clean_name, load_csv_data

CSV_PATH = r"C:\Users\rajeev\Desktop\stock_profile.csv"

def debug():
    name_map, symbol_map = load_csv_data()
    print(f"Loaded {len(name_map)} name-based keys.")
    
    # Check for Barry
    for k in name_map.keys():
        if "barry" in k:
            print(f"FOUND 'barry' variant in keys: '{k}'")
            
    # Check what's in the DB for Barry
    conn = sqlite3.connect('career_revolution.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM job_sources WHERE name LIKE '%Barry%'")
    rows = cursor.fetchall()
    for r in rows:
        dbname = r[0]
        cname = clean_name(dbname)
        print(f"DB Name: '{dbname}' -> Cleaned: '{cname}'")
        if cname in name_map:
            print("  MATCH FOUND!")
        else:
            print("  STILL NO MATCH.")
    
    conn.close()

if __name__ == "__main__":
    debug()
