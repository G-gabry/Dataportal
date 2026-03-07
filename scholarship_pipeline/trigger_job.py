import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env.vm")

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env.vm")

engine = create_engine(DB_URL)

def trigger_job():
    print(f"[{datetime.now().isoformat()}] Inserting a manual scrape job...")
    try:
        with engine.connect() as conn:
            # 1. We need a valid source_id to scrape. Let's get the first active source from the db.
            source = conn.execute(text("SELECT id, name FROM sources WHERE is_active = true LIMIT 1")).fetchone()
            
            if not source:
                print("Error: No active sources found in the database. Ensure you have added at least one source.")
                return
            
            source_id, source_name = source
            print(f"Found active source: {source_name} (ID: {source_id})")

            # 2. Insert the pending job
            # Generating a new UUID for the job
            job_id = str(uuid.uuid4())
            conn.execute(
                text("""
                INSERT INTO scrape_jobs (id, source_id, job_type, status, created_at, updated_at) 
                VALUES (:id, :source_id, 'FULL_SCRAPE', 'PENDING', NOW(), NOW())
                """),
                {"id": job_id, "source_id": source_id}
            )
            conn.commit()
            print(f"✅ Successfully queued a 'FULL_SCRAPE' job (ID: {job_id}) for '{source_name}'.")
            print("The worker.py script should pick this up within 10 seconds!")
            
    except Exception as e:
        print(f"❌ Error inserting job: {e}")

if __name__ == "__main__":
    trigger_job()
