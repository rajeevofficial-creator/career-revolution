import sys
import os
import csv
import sqlite3
from difflib import get_close_matches
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobSource

CSV_PATH = r"C:\Users\rajeev\Desktop\stock_profile.csv"

def clean_name(name):
    """Clean company name for better matching."""
    if not name: return ""
    name = str(name).lower().strip()
    for suffix in [" ag", " ltd", " sa", " inc", " plc", " group", " holding", " s.a.", " corp", " corporation"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name

def find_best_col(cols, candidates):
    for c in candidates:
        if c in cols: return c
    return None

def load_csv_data():
    """Load name -> (Symbol, Sector, Industry) from CSV with flexible headers."""
    name_data = {} # clean_name -> {symbol, sector, industry}
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found at {CSV_PATH}")
        return {}
    
    try:
        # Try different encodings
        for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(CSV_PATH, mode='r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    if not fieldnames: continue
                    
                    # Find relevant columns
                    name_col = find_best_col(fieldnames, ['name', 'description', 'full_name'])
                    symbol_col = find_best_col(fieldnames, ['symbol', 'ticker', 'stock_id'])
                    sector_col = find_best_col(fieldnames, ['sector_new', 'sector', 'industry_group'])
                    industry_col = find_best_col(fieldnames, ['industry_new', 'industry', 'sub_industry'])
                    
                    if not name_col:
                        print(f"[{enc}] Could not find a name column in {fieldnames}")
                        continue
                        
                    print(f"[{enc}] Using columns: name={name_col}, symbol={symbol_col}, sector={sector_col}, industry={industry_col}")
                    
                    for row in reader:
                        full_name = row.get(name_col)
                        if full_name:
                            cname = clean_name(full_name)
                            name_data[cname] = {
                                "symbol": row.get(symbol_col),
                                "sector": row.get(sector_col),
                                "industry": row.get(industry_col)
                            }
                    
                    if name_data:
                        print(f"[{enc}] Successfully loaded {len(name_data)} entries.")
                        return name_data
            except Exception as e:
                print(f"[{enc}] Error: {e}")
                
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return name_data

def enrich():
    db = SessionLocal()
    
    csv_info = load_csv_data()
    if not csv_info:
        print("FAILED to load any data from CSV. Enrichment aborted.")
        db.close()
        return

    sources = db.query(JobSource).all()
    updated_count = 0
    csv_names = list(csv_info.keys())
    
    for src in sources:
        target_name = clean_name(src.name)
        match = None
        
        # Exact match of cleaned name
        if target_name in csv_info:
            match = csv_info[target_name]
        else:
            # Substring/Close match
            close = get_close_matches(target_name, csv_names, n=1, cutoff=0.7) # lowered cutoff for better reach
            if close:
                match = csv_info[close[0]]
                
        if match:
            src.sector = match['sector']
            src.industry = match['industry']
            updated_count += 1
            print(f"Enriched {src.name}: Sector={src.sector}, Industry={src.industry}")
        else:
            print(f"No match for {src.name}")
        
    db.commit()
    db.close()
    print(f"Enrichment complete. Updated {updated_count} sources.")

if __name__ == "__main__":
    enrich()
