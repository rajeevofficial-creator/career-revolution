import asyncio
import logging
from app.models.database import SessionLocal, JobOpportunity, JobMatch
from app.services.ingestion_service import IngestionService
from agents.job_search_agent.job_finder_agent import JobFinderAgent
from app.config import settings

# Configure explicit logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Professional-Grade Scraper Script...")
    db = SessionLocal()
    
    # Optional: Wipe corrupt data again just to be 100% sure we start clean
    logger.info("Wiping old/corrupt job data from database for a fresh crawl...")
    db.query(JobMatch).delete()
    db.query(JobOpportunity).delete()
    db.commit()
    
    # Initialize the agents with the LATEST code
    from app.models.database import User, UserProfile
    
    # Ensure we have a real user and profile in the DB to avoid SQL errors
    profile = db.query(UserProfile).first()
    if not profile:
        logger.info("No profile found. Creating a temporary user/profile for the crawl...")
        user = User(email="crawler@temp.local", password_hash="n/a", full_name="Temp Crawler")
        db.add(user)
        db.flush()
        profile = UserProfile(user_id=user.id, location="Switzerland", desired_job_title="Software Engineer")
        db.add(profile)
        db.commit()
    else:
        logger.info(f"Using existing profile for user {profile.user_id}")
    
    ingestor = IngestionService()
    finder = JobFinderAgent(db)
    
    logger.info("Executing Job Finder Universal Ingestion...")
    # Run the universal sourcing (this hits the DB sources and runs IngestionService)
    try:
        await finder.find_jobs_from_sources(profile.user_id, loc_override=None, deep_check=False)
        logger.info("Scraping completed successfully!")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        
    # Let's verify what got saved
    jobs = db.query(JobOpportunity).all()
    logger.info(f"\n--- SCRAPE RESULTS: {len(jobs)} Unique Jobs Captured ---")
    
    # Print the first 20 to prove they are clean
    for j in jobs[:20]:
        logger.info(f"CAPTURED -> Title: '{j.title[:40]}' | Company: '{j.company}' | URL: {j.application_url}")

if __name__ == "__main__":
    asyncio.run(main())
