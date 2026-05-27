"""Run Phase 2 — align ingested jobs to user profile."""
import asyncio, logging, sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("align_jobs.log", encoding="utf-8"),
    ]
)

async def main():
    from app.models.database import SessionLocal
    from agents.job_search_agent.job_finder_agent import JobFinderAgent

    db = SessionLocal()
    try:
        agent = JobFinderAgent(db)
        print("\n" + "="*60)
        print("Phase 2 — Align Jobs to User (user_id=1)")
        print("="*60 + "\n")

        result = await agent.align_jobs_to_user(user_id=1, deep_check=False)

        print("\n" + "="*60)
        print("ALIGNMENT RESULT:")
        for k, v in result.items():
            print(f"  {k}: {v}")
        print("="*60 + "\n")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
