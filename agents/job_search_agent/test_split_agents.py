
import asyncio
import sys
import os
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, User, UserProfile, JobSource, JobOpportunity
from agents.job_search_agent.job_sourcing_agent import JobSourcingAgent
from agents.job_search_agent.job_finder_agent import JobFinderAgent

async def test_workflow():
    db = SessionLocal()
    try:
        # 1. Get a test user (ideally one with a profile)
        user = db.query(User).first()
        if not user:
            print("No users found in database. Please run simple_upload_test.py or register a user first.")
            return

        print(f"Testing workflow for User: {user.email} (ID: {user.id})")
        
        # 2. Run Sourcing Agent
        print("\n--- Phase 1: Job Sourcing ---")
        sourcing_agent = JobSourcingAgent(db)
        sourcing_result = await sourcing_agent.run_sourcing_pipeline(user.id, force_update=True)
        print(f"Sourcing Result: {json.dumps(sourcing_result, indent=2)}")
        
        # Verify sources in DB
        sources = db.query(JobSource).filter(JobSource.is_active == True).all()
        print(f"Verified {len(sources)} active sources in database.")
        for s in sources:
            print(f" - {s.name} ({s.source_type}): {s.url}")

        # 3. Run Finder Agent
        print("\n--- Phase 2: Job Finding ---")
        finder_agent = JobFinderAgent(db)
        finder_result = await finder_agent.find_jobs_from_sources(user.id)
        print(f"Finding Result: {json.dumps(finder_result, indent=2)}")
        
        # Verify jobs in DB
        jobs = db.query(JobOpportunity).filter(JobOpportunity.user_id == user.id).all()
        print(f"Verified {len(jobs)} job opportunities in database for this user.")
        for j in sorted(jobs, key=lambda x: x.relevance_score or 0, reverse=True)[:3]:
            print(f" - [{j.relevance_score}] {j.title} at {j.company}")
            print(f"   URL: {j.application_url}")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import json
    asyncio.run(test_workflow())
