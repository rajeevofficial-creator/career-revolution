
import sys
import os
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobOpportunity, UserProfile
from agents.job_search_agent.job_finder_agent import JobFinderAgent

def run():
    db = SessionLocal()
    agent = JobFinderAgent(db)
    
    # Get all jobs
    jobs = db.query(JobOpportunity).all()
    print(f"Recalculating scores for {len(jobs)} jobs...")
    
    updated_count = 0
    for job in jobs:
        profile = db.query(UserProfile).filter(UserProfile.user_id == job.user_id).first()
        if not profile:
            continue
            
        old_score = job.relevance_score
        # Calculate new heuristic score
        new_score = agent._calculate_heuristic_score(job.title, job.description or "", profile)
        
        if old_score != new_score:
            job.relevance_score = new_score
            updated_count += 1
            
    db.commit()
    print(f"Done. Updated {updated_count} job scores.")
    db.close()

if __name__ == "__main__":
    run()
