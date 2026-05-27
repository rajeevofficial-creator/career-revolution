"""Direct sync runner - bypasses HTTP to run the pipeline with full log output."""
import asyncio
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sync_run3.log", encoding="utf-8"),
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

async def main():
    from app.models.database import SessionLocal
    from agents.job_search_agent.job_sourcing_agent import JobSourcingAgent
    db = SessionLocal()
    try:
        agent = JobSourcingAgent(db)
        print("\n" + "="*60)
        print("Starting Sync & Refine Sources - Switzerland")
        print("Time: " + datetime.now().isoformat())
        print("="*60 + "\n")
        result = await agent.run_sourcing_pipeline(
            user_id=1,
            country="Switzerland",
            force_update=True,
        )
        print("\n" + "="*60)
        print("SYNC RESULT:")
        for k, v in result.items():
            print("  " + str(k) + ": " + str(v))
        print("="*60 + "\n")
        return result
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
