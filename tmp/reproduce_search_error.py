import requests
import json

BASE_URL = "http://localhost:8005"

# We need an auth token. Since I can't easily get one, I'll try to use the db directly to simulate the query logic.
from sqlalchemy import create_engine, and_, or_, not_
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent dir to path to import models
sys.path.append(os.path.join(os.getcwd(), 'app'))
from models.database import Base, JobOpportunity, JobSource, JobMatch, User

engine = create_engine(r'sqlite:///c:\Users\rajeev\career_revolution\career_revolution.db')
Session = sessionmaker(bind=engine)
db = Session()

try:
    source_country = "Switzerland"
    user_id = 1 # Assuming user 1 exists
    
    # Simulate main.py logic
    query = db.query(JobOpportunity, JobMatch.relevance_score.label('match_score'), JobMatch.is_verified.label('match_verified')).outerjoin(
        JobMatch,
        and_(JobMatch.job_opportunity_id == JobOpportunity.id, JobMatch.user_id == user_id)
    ).filter(
        JobOpportunity.is_live == True
    )
    
    print("Base query constructed.")
    
    if source_country:
        print(f"Joining JobSource for country: {source_country}")
        query = query.join(JobSource).filter(JobSource.country == source_country)
        
    print("Executing query...")
    results = query.all()
    print(f"Success! Found {len(results)} jobs.")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
