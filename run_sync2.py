import sys, asyncio, logging, json
sys.path.insert(0, r'c:\Users\rajeev\career_revolution')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(r'c:\Users\rajeev\career_revolution\sync_run2.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

from app.models.database import SessionLocal
from agents.job_search_agent.job_sourcing_agent import JobSourcingAgent

async def main():
    db = SessionLocal()
    try:
        agent = JobSourcingAgent(db)
        # Pass country explicitly to be safe
        result = await agent.run_sourcing_pipeline(user_id=1, country='Switzerland', force_update=True)
        print("\n=== RESULT ===")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()

asyncio.run(main())
