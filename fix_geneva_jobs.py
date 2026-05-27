
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, JobOpportunity, JobMatch, UserProfile
from agents.job_search_agent.job_finder_agent import JobFinderAgent

async def run():
    db = SessionLocal()
    agent = JobFinderAgent(db)
    user_id = 1
    prof = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    # 1. Normalize all Geneva jobs
    import sqlalchemy
    jobs = db.query(JobOpportunity).filter(
        sqlalchemy.or_(
            JobOpportunity.location.ilike('%Genève%'),
            JobOpportunity.location.ilike('%Geneva%')
        )
    ).all()
    
    print(f"Refining {len(jobs)} Geneva/Romandie jobs...")
    
    for j in jobs:
        # Force correct metadata for existing jobs
        j.experience_level = 'Mid-Senior Level'
        j.job_type = 'Permanent'
        j.is_live = True
        
        # Re-calculate score with NEW improved IT logic
        score = agent._calculate_heuristic_score(j.title, j.description or '', prof)
        
        # Upsert Match
        match = db.query(JobMatch).filter(
            JobMatch.job_opportunity_id == j.id, 
            JobMatch.user_id == user_id
        ).first()
        
        if match:
            match.relevance_score = score
        else:
            db.add(JobMatch(
                job_opportunity_id=j.id, 
                user_id=user_id, 
                relevance_score=score
            ))
            
        print(f" - {j.title[:30]} | New Score: {score}")

    db.commit()
    print("Optimization Complete.")
    db.close()

if __name__ == "__main__":
    asyncio.run(run())
