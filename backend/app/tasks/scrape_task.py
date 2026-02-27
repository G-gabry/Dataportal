"""
Production Scrape Pipeline - Uses Firecrawl VM for crawling and AI for extraction.

Pipeline:
1. CRAWL - Use Firecrawl VM to crawl entire site (async job)
2. FILTER - Filter relevant pages using keywords
3. EXTRACT - Use AI to extract simplified data (Name, URL, Country, Summary)
4. SAVE - Save items to database
"""
import asyncio
import re
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.source import Source
from app.models.discovered_url import DiscoveredURL
from app.models.item import Item
from app.models.item_schema import ItemSchema
from app.models.scrape_job import ScrapeJob
from app.models.ai_log import AILog
from app.models.setting import Setting
from app.models.enums import (
    JobStatus, URLStatus, RelevanceStatus, PriorityLevel, ItemStatus, ItemType
)
from app.integrations.firecrawl import FirecrawlClient, ScrapeResult
from app.ai.factory import get_ai_provider
from app.ai.base import TaskType


# Keywords for filtering relevant pages
RELEVANCE_KEYWORDS = {
    ItemType.PROGRAM: [
        "program", "programme", "course", "degree", "master", "msc", "phd",
        "bachelor", "bsc", "graduate", "admission", "study", "curriculum"
    ],
    ItemType.SCHOLARSHIP: [
        "scholarship", "fellowship", "grant", "funding", "financial aid",
        "award", "bursary", "stipend"
    ],
    ItemType.CONFERENCE: [
        "conference", "symposium", "workshop", "summit", "congress",
        "call for papers", "submission deadline"
    ],
    ItemType.EXCHANGE: [
        "exchange", "study abroad", "mobility", "erasmus", "international",
        "semester abroad", "partner university"
    ],
}


def run_scrape_job(source_id: UUID, job_type: str, user_id: UUID):
    """Entry point for background scrape job"""
    asyncio.run(_run_scrape_job_async(source_id, job_type, user_id))


async def _run_scrape_job_async(source_id: UUID, job_type: str, user_id: UUID):
    """Async scrape job execution"""
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return

        job = ScrapeJob(
            source_id=source_id,
            job_type=job_type,
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
            current_step="Initializing"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        pipeline = ScrapePipeline(db, job, source)
        await pipeline.run()

    except Exception as e:
        import traceback
        print(f"[Scrape] ERROR: {str(e)}")
        print(traceback.format_exc())
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.error_log = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


class ScrapePipeline:
    """Production scraping pipeline using Firecrawl VM"""

    def __init__(self, db: Session, job: ScrapeJob, source: Source):
        self.db = db
        self.job = job
        self.source = source
        self.firecrawl = FirecrawlClient()

    async def run(self):
        """Execute the scraping pipeline"""
        try:
            # Step 1: Crawl the site using Firecrawl VM
            await self._update_step("Starting crawl job", 5)
            pages = await self._crawl_site()

            if not pages:
                print("[Scrape] No pages crawled")
                await self._complete_job()
                return

            # Step 2: Filter relevant pages
            await self._update_step("Filtering relevant pages", 30)
            relevant_pages = self._filter_relevant_pages(pages)

            if not relevant_pages:
                print("[Scrape] No relevant pages found")
                await self._complete_job()
                return

            # Step 3: Save discovered URLs
            await self._update_step("Saving discovered URLs", 40)
            await self._save_discovered_urls(relevant_pages)

            # Step 4: Extract data using AI
            await self._update_step("Extracting data", 50)
            await self._extract_data(relevant_pages)

            # Complete
            await self._complete_job()

        except Exception as e:
            self.job.status = JobStatus.FAILED
            self.job.error_log = str(e)
            self.job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise

    async def _update_step(self, step: str, progress: int):
        """Update job progress"""
        self.job.current_step = step
        self.job.progress_percent = progress
        self.db.commit()
        print(f"[Scrape] {step} ({progress}%)")

    async def _complete_job(self):
        """Mark job as completed"""
        self.job.status = JobStatus.COMPLETED
        self.job.current_step = "Completed"
        self.job.progress_percent = 100
        self.job.completed_at = datetime.now(timezone.utc)

        # Update source stats
        self.source.last_scraped_at = datetime.now(timezone.utc)
        self.source.urls_discovered_count = self.db.query(DiscoveredURL).filter(
            DiscoveredURL.source_id == self.source.id
        ).count()
        self.source.items_extracted_count = self.db.query(Item).filter(
            Item.source_id == self.source.id
        ).count()

        self.db.commit()
        print(f"[Scrape] Job completed. URLs: {self.job.urls_discovered}, Items: {self.job.items_extracted}")

    async def _crawl_site(self) -> List[ScrapeResult]:
        """Crawl the entire site using Firecrawl VM crawl endpoint"""
        print(f"[Scrape] Starting crawl of {self.source.base_url}")

        include_paths = list(self.source.include_patterns) if self.source.include_patterns else None
        exclude_paths = list(self.source.exclude_patterns) if self.source.exclude_patterns else None

        # Start the crawl job
        crawl_result = await self.firecrawl.start_crawl(
            url=self.source.base_url,
            limit=500,
            max_depth=7,
            wait_for=5000,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
        )

        self.job.firecrawl_calls += 1

        if not crawl_result.success:
            print(f"[Scrape] Crawl failed: {crawl_result.error}")
            self.job.error_log = f"Crawl failed: {crawl_result.error}"
            return []

        job_id = crawl_result.job_id
        print(f"[Scrape] Crawl job started: {job_id}")

        # Poll for completion
        async def on_progress(completed: int, total: int):
            progress = 5 + int(20 * completed / max(total, 1))
            await self._update_step(f"Crawling: {completed}/{total} pages", progress)

        result = await self.firecrawl.poll_crawl_until_done(
            job_id=job_id,
            poll_interval=10,
            max_wait=1800,  # 30 minutes max
            on_progress=on_progress,
        )

        if not result.success:
            print(f"[Scrape] Crawl polling failed: {result.error}")
            return []

        self.job.urls_discovered = len(result.pages)
        self.db.commit()

        print(f"[Scrape] Crawl completed: {len(result.pages)} pages")
        return result.pages

    def _filter_relevant_pages(self, pages: List[ScrapeResult]) -> List[ScrapeResult]:
        """Filter pages based on relevance keywords"""
        target_types = [
            ItemType(t) if isinstance(t, str) else t
            for t in self.source.target_item_types
        ]

        # Collect keywords for target types
        keywords = set()
        for item_type in target_types:
            keywords.update(RELEVANCE_KEYWORDS.get(item_type, []))

        relevant = []
        for page in pages:
            if not page.markdown:
                continue

            content_lower = page.markdown.lower()
            url_lower = page.url.lower()

            # Check if any keyword matches
            if any(kw in content_lower or kw in url_lower for kw in keywords):
                relevant.append(page)

        self.job.urls_relevant = len(relevant)
        self.db.commit()

        print(f"[Scrape] Filtered to {len(relevant)} relevant pages")
        return relevant

    async def _save_discovered_urls(self, pages: List[ScrapeResult]):
        """Save discovered URLs to database"""
        for page in pages:
            existing = self.db.query(DiscoveredURL).filter(
                DiscoveredURL.source_id == self.source.id,
                DiscoveredURL.url == page.url
            ).first()

            if existing:
                existing.raw_markdown = page.markdown
                existing.content_hash = hashlib.md5((page.markdown or "").encode()).hexdigest()
                existing.status = URLStatus.SCRAPED
                existing.relevance = RelevanceStatus.RELEVANT
                existing.last_scraped_at = datetime.now(timezone.utc)
            else:
                discovered = DiscoveredURL(
                    source_id=self.source.id,
                    url=page.url,
                    url_path=page.url.replace(self.source.base_url, ""),
                    raw_markdown=page.markdown,
                    content_hash=hashlib.md5((page.markdown or "").encode()).hexdigest(),
                    relevance=RelevanceStatus.RELEVANT,
                    status=URLStatus.SCRAPED,
                    discovered_at=datetime.now(timezone.utc),
                    last_scraped_at=datetime.now(timezone.utc),
                )
                self.db.add(discovered)

        self.job.urls_scraped = len(pages)
        self.db.commit()

    async def _extract_data(self, pages: List[ScrapeResult]):
        """
        Process pages in batches of 5. Each batch → AI extracts ALL items found.
        Supports multiple items per page (listing sites like mastersportal, findamasters).
        Deduplicates by item URL to avoid duplicates across batches.
        """
        ai_provider = get_ai_provider(self.db, TaskType.EXTRACTION)

        target_types = [
            ItemType(t) if isinstance(t, str) else t
            for t in self.source.target_item_types
        ]

        # Track URLs already saved in this job to avoid duplicates
        seen_urls: set = set()

        # Load URLs of existing items for this source to avoid re-saving unchanged ones
        existing_items = self.db.query(Item).filter(Item.source_id == self.source.id).all()
        existing_by_url: Dict[str, Item] = {}
        for ei in existing_items:
            url = (ei.data or {}).get("url", "")
            if url:
                existing_by_url[url] = ei

        # Process in batches of 5 pages
        BATCH_SIZE = 5
        batches = [pages[i:i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]
        total_batches = len(batches)

        print(f"[Scrape] Extracting from {len(pages)} pages in {total_batches} batches")

        for batch_idx, batch in enumerate(batches):
            progress = 50 + int(45 * batch_idx / max(total_batches, 1))
            await self._update_step(
                f"Extracting batch {batch_idx + 1}/{total_batches}", progress
            )

            batch_content: Dict[str, str] = {}
            for page in batch:
                if page.markdown:
                    batch_content[page.url] = page.markdown[:3000]

            if not batch_content:
                continue

            for item_type in target_types:
                items_data = await self._extract_items_from_batch(
                    batch_content, item_type, ai_provider
                )

                for item_data in items_data:
                    item_url = item_data.get("url", "").rstrip("/")
                    if not item_url or item_url in seen_urls:
                        continue
                    seen_urls.add(item_url)

                    if item_url in existing_by_url:
                        # Update existing item
                        existing_by_url[item_url].data = item_data
                        existing_by_url[item_url].extraction_confidence = 85
                        existing_by_url[item_url].extracted_at = datetime.now(timezone.utc)
                    else:
                        item = Item(
                            source_id=self.source.id,
                            item_type=item_type,
                            data=item_data,
                            extraction_confidence=85,
                            status=ItemStatus.DRAFT,
                            extracted_at=datetime.now(timezone.utc),
                        )
                        self.db.add(item)
                        self.job.items_extracted += 1

            self.db.commit()

        # Mark all pages as extracted
        for page in pages:
            disc = self.db.query(DiscoveredURL).filter(
                DiscoveredURL.source_id == self.source.id,
                DiscoveredURL.url == page.url
            ).first()
            if disc:
                disc.status = URLStatus.EXTRACTED

        self.db.commit()
        print(f"[Scrape] Extraction complete. Total items: {self.job.items_extracted}")

    async def _extract_items_from_batch(
        self,
        batch_content: Dict[str, str],
        item_type: ItemType,
        ai_provider,
    ) -> List[Dict[str, Any]]:
        """
        Send a batch of pages to Gemini and extract ALL items found.
        Returns a list of item dicts (can be empty if nothing found).
        """
        type_name = item_type.value.lower()

        prompt = f"""You are extracting {type_name} opportunities from web pages.

Pages from {self.source.base_url}:
{json.dumps(batch_content, ensure_ascii=False)[:14000]}

Extract ALL {type_name} opportunities found across these pages.
For each one return:
- name: Full name of the {type_name}
- url: Direct URL (use the page URL if no specific URL is given)
- country: Country where it is based or offered
- summary: 2-3 sentences describing it
- deadline: Application deadline if mentioned, else null
- funding: Funding amount or type if mentioned, else null

Return ONLY a JSON array, no other text. If nothing found return [].
[
  {{
    "name": "...",
    "url": "...",
    "country": "...",
    "summary": "...",
    "deadline": null,
    "funding": null
  }}
]"""

        try:
            result = await ai_provider.generate_json(prompt)

            ai_log = AILog(
                task_type="EXTRACT_BATCH",
                model_used=ai_provider.model,
                provider=ai_provider.provider_name,
                job_id=self.job.id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(ai_log)

            # Result may be a list or a dict with a list inside
            parsed = result.parsed_json
            if isinstance(parsed, list):
                print(f"[Scrape] Batch extracted {len(parsed)} {type_name}(s)")
                return parsed
            if isinstance(parsed, dict):
                # Sometimes AI wraps in {"items": [...]}
                for key in ("items", "results", "data", type_name + "s"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]

            return []

        except Exception as e:
            print(f"[Scrape] Batch extraction error: {e}")
            return []
