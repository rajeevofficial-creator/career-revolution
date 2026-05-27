"""Run Refresh Jobs (Phase 1 - ingest) directly."""
import asyncio, logging, sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("refresh_jobs.log", encoding="utf-8"),
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

async def main():
    from app.models.database import SessionLocal
    from agents.job_search_agent.job_finder_agent import JobFinderAgent

    db = SessionLocal()
    try:
        agent = JobFinderAgent(db)
        print("\n" + "="*60)
        print("Starting Refresh Jobs (Phase 1 - Ingest) - Switzerland")
        print("Time: " + datetime.now().isoformat())
        print("="*60 + "\n")

        result = await agent.ingest_jobs(country="Switzerland")

        print("\n" + "="*60)
        print("REFRESH JOBS RESULT:")
        for k, v in result.items():
            print("  " + str(k) + ": " + str(v))
        print("="*60 + "\n")
        return result
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
