"""Test scrape script - runs scrape on first source of each type"""
import asyncio
import os
import sys

# Set up environment
os.chdir('/Users/ahmedali/Desktop/data-portal/backend')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('/Users/ahmedali/Desktop/data-portal/.env', override=True)

from app.core.database import SessionLocal
from app.models.source import Source
from app.models.item import Item
from app.models.enums import ItemType, ItemStatus
from app.tasks.scrape_task import ScrapePipeline, ScrapeJob, JobStatus
from datetime import datetime, timezone
from uuid import uuid4


async def test_scrape_one_source(source_type: str):
    """Test scrape on first source of given type"""
    db = SessionLocal()

    try:
        # Get first source of this type
        source = db.query(Source).filter(Source.type == source_type).first()
        if not source:
            print(f"No source found for type: {source_type}")
            return

        print(f"\n{'='*60}")
        print(f"Testing scrape for: {source.name}")
        print(f"Type: {source_type}")
        print(f"URL: {source.base_url}")
        print(f"{'='*60}")

        # Create job record
        job = ScrapeJob(
            source_id=source.id,
            job_type="test_scrape",
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            current_step="Initializing"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Run pipeline
        pipeline = ScrapePipeline(db, job, source)
        await pipeline.run()

        print(f"\nJob completed: {job.status.value}")
        print(f"URLs discovered: {job.urls_discovered}")
        print(f"URLs scraped: {job.urls_scraped}")
        print(f"Items extracted: {job.items_extracted}")

        # Show extracted items
        items = db.query(Item).filter(Item.source_id == source.id).limit(5).all()
        print(f"\nExtracted items ({len(items)}):")
        for item in items:
            print(f"  - {item.data.get('name', 'N/A')[:50]}")
            print(f"    Country: {item.data.get('country', 'N/A')}")
            print(f"    Summary: {item.data.get('summary', 'N/A')[:80]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def main():
    # Test one source per type
    types = ['UNIVERSITY', 'SCHOLARSHIP_ORG', 'CONFERENCE_ORG', 'EXCHANGE_ORG']

    for source_type in types:
        await test_scrape_one_source(source_type)
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
