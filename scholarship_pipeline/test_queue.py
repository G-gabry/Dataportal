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

def setup_and_trigger():
    print(f"[{datetime.now().isoformat()}] Setting up database tables and triggering job...")
    try:
        with engine.connect() as conn:
            # 1. Create the enum type if it doesn't exist
            # PostgreSQL requires catching duplicate type creation or checking if it exists
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE jobstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # 2. Create the scrape_jobs table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS scrape_jobs (
                    id UUID PRIMARY KEY,
                    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
                    job_type VARCHAR(50) NOT NULL,
                    status jobstatus DEFAULT 'PENDING',
                    current_step VARCHAR(100),
                    progress_percent INTEGER DEFAULT 0,
                    urls_discovered INTEGER DEFAULT 0,
                    urls_relevant INTEGER DEFAULT 0,
                    urls_scraped INTEGER DEFAULT 0,
                    items_extracted INTEGER DEFAULT 0,
                    items_updated INTEGER DEFAULT 0,
                    ai_tokens_used INTEGER DEFAULT 0,
                    ai_cost_usd NUMERIC(10, 4) DEFAULT 0,
                    firecrawl_calls INTEGER DEFAULT 0,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    error_log TEXT,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
                );
            """))
            print("Verified 'scrape_jobs' table exists.")

            # 3. Find a valid source to scrape
            source = conn.execute(text("SELECT id, name FROM sources WHERE is_active = true LIMIT 1")).fetchone()
            
            if not source:
                print("Error: No active sources found in the database. Ensure you have added at least one source.")
                return
            
            source_id, source_name = source
            print(f"Found active source: {source_name} (ID: {source_id})")

            # 4. Insert the pending job
            job_id = str(uuid.uuid4())
            conn.execute(
                text("""
                INSERT INTO scrape_jobs (id, source_id, job_type, status, created_at) 
                VALUES (:id, :source_id, 'FULL_SCRAPE', 'PENDING', NOW())
                """),
                {"id": job_id, "source_id": source_id}
            )
            conn.commit()
            print(f"✅ Successfully queued a 'FULL_SCRAPE' job (ID: {job_id}) for '{source_name}'.")
            print("Your worker.py script will pick this up automatically within 10 seconds!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    setup_and_trigger()
