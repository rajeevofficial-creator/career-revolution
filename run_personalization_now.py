import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.models.database import SessionLocal
from agents.job_search_agent.job_finder_agent import JobFinderAgent

async def run():
    db = SessionLocal()
    agent = JobFinderAgent(db)
    # Target common user ID 1
    user_id = 1
    print(f"Triggering Stage 2 Personalization for User {user_id}...")
    result = await agent.personalize_market_jobs(user_id)
    print(f"Result: {result}")
    db.close()

if __name__ == "__main__":
    asyncio.run(run())
