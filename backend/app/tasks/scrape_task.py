import asyncio
import re
import hashlib
from datetime import datetime
from typing import List, Optional
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
from app.integrations.firecrawl import FirecrawlClient
from app.ai.factory import get_ai_provider
from app.ai.base import TaskType, AIResponse


def run_scrape_job(source_id: UUID, job_type: str, user_id: UUID):
    """Entry point for background scrape job"""
    asyncio.run(_run_scrape_job_async(source_id, job_type, user_id))


async def _run_scrape_job_async(source_id: UUID, job_type: str, user_id: UUID):
    """Async scrape job execution"""
    db = SessionLocal()

    try:
        # Get source
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return

        # Create job record
        job = ScrapeJob(
            source_id=source_id,
            job_type=job_type,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
            created_by=user_id,
            current_step="Initializing"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        scraper = ScrapePipeline(db, job, source)
        await scraper.run()

    except Exception as e:
        # Update job with error
        import traceback
        print(f"[Scrape] ERROR: {str(e)}")
        print(traceback.format_exc())
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.error_log = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


class ScrapePipeline:
    """Main scraping pipeline orchestrator"""

    def __init__(self, db: Session, job: ScrapeJob, source: Source):
        self.db = db
        self.job = job
        self.source = source
        self.firecrawl = FirecrawlClient()

    async def run(self):
        """Execute the full scraping pipeline"""
        try:
            # Step 1: Discover URLs
            await self._update_step("Discovering URLs", 10)
            urls = await self._discover_urls()

            if not urls:
                await self._complete_job()
                return

            # Step 2: Pre-filter URLs
            await self._update_step("Pre-filtering URLs", 20)
            filtered_urls = self._pre_filter_urls(urls)

            # Step 3: AI classify URLs
            await self._update_step("Classifying URLs", 30)
            relevant_urls = await self._classify_urls(filtered_urls)

            if not relevant_urls:
                await self._complete_job()
                return

            # Step 4: Scrape relevant URLs
            await self._update_step("Scraping content", 50)
            scraped_urls = await self._scrape_urls(relevant_urls)

            # Step 5: Classify content
            await self._update_step("Analyzing content", 70)
            await self._classify_content(scraped_urls)

            # Step 6: Extract data
            await self._update_step("Extracting data", 85)
            await self._extract_data(scraped_urls)

            # Complete
            await self._complete_job()

        except Exception as e:
            self.job.status = JobStatus.FAILED
            self.job.error_log = str(e)
            self.job.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    async def _update_step(self, step: str, progress: int):
        """Update job progress"""
        self.job.current_step = step
        self.job.progress_percent = progress
        self.db.commit()

    async def _complete_job(self):
        """Mark job as completed"""
        self.job.status = JobStatus.COMPLETED
        self.job.current_step = "Completed"
        self.job.progress_percent = 100
        self.job.completed_at = datetime.utcnow()

        # Update source stats
        self.source.last_scraped_at = datetime.utcnow()
        self.source.urls_discovered_count = self.db.query(DiscoveredURL).filter(
            DiscoveredURL.source_id == self.source.id
        ).count()
        self.source.items_extracted_count = self.db.query(Item).filter(
            Item.source_id == self.source.id
        ).count()

        self.db.commit()

    async def _discover_urls(self) -> List[str]:
        """Discover all URLs from the source domain"""
        result = await self.firecrawl.map_domain(self.source.base_url)

        self.job.firecrawl_calls += 1

        if not result.success:
            self.job.error_log = f"Map domain failed: {result.error}"
            return []

        self.job.urls_discovered = len(result.urls)
        self.db.commit()

        return result.urls

    def _pre_filter_urls(self, urls: List[str]) -> List[str]:
        """Pre-filter URLs using patterns (no AI cost)"""
        print(f"[Scrape] Pre-filtering {len(urls)} URLs")
        # Get scraping config
        setting = self.db.query(Setting).filter(Setting.key == "scraping_config").first()
        default_excludes = setting.value.get("default_exclude_patterns", []) if setting else []

        # Combine with source-specific patterns
        exclude_patterns = default_excludes + (self.source.exclude_patterns or [])
        include_patterns = self.source.include_patterns or []
        print(f"[Scrape] Exclude patterns: {exclude_patterns}")

        filtered = []
        for url in urls:
            # Skip if matches any exclude pattern
            excluded = False
            for pattern in exclude_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    print(f"[Scrape] Excluding: {url} (matched: {pattern})")
                    excluded = True
                    break
            if excluded:
                continue

            # If include patterns specified, URL must match at least one
            if include_patterns:
                if any(re.search(pattern, url, re.IGNORECASE) for pattern in include_patterns):
                    filtered.append(url)
            else:
                filtered.append(url)

        print(f"[Scrape] After pre-filter: {len(filtered)} URLs remain")
        for url in filtered:
            print(f"[Scrape] Kept: {url}")
        return filtered

    async def _classify_urls(self, urls: List[str]) -> List[str]:
        """Classify URLs for relevance using AI"""
        print(f"[Scrape] Classifying {len(urls)} URLs")
        if not urls:
            print("[Scrape] No URLs to classify")
            return []

        # Get AI provider for URL classification
        ai_provider = get_ai_provider(self.db, TaskType.URL_CLASSIFICATION)
        print(f"[Scrape] Using AI provider: {ai_provider.provider_name}")

        # Build context for classification
        # Handle both enum and string values from database
        target_types = [t.value if hasattr(t, 'value') else t for t in self.source.target_item_types]
        source_type = self.source.type.value if hasattr(self.source.type, 'value') else self.source.type
        context = f"Looking for pages about: {', '.join(target_types)}. Source: {self.source.name} ({source_type})"

        # Batch process URLs
        batch_size = 50
        relevant_urls = []

        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]

            results = await ai_provider.classify_urls(batch, context)

            # Log AI usage
            # Note: classify_urls internally calls generate_json, we'd need to capture the response
            # For simplicity, we estimate tokens here
            ai_log = AILog(
                task_type="CLASSIFY_URLS",
                model_used=ai_provider.model,
                provider=ai_provider.provider_name,
                job_id=self.job.id,
                input_tokens=len(context) + sum(len(u) for u in batch),
                output_tokens=len(str(results)),
                created_at=datetime.utcnow()
            )
            self.db.add(ai_log)

            # Process results
            for result in results:
                url = result.get("url")
                is_relevant = result.get("is_relevant", False)

                # Save discovered URL
                existing = self.db.query(DiscoveredURL).filter(
                    DiscoveredURL.source_id == self.source.id,
                    DiscoveredURL.url == url
                ).first()

                if existing:
                    existing.relevance = RelevanceStatus.RELEVANT if is_relevant else RelevanceStatus.NOT_RELEVANT
                    existing.relevance_score = result.get("confidence", 0) * 100
                    existing.relevance_reason = result.get("reason", "")
                    existing.last_classified_at = datetime.utcnow()
                else:
                    discovered = DiscoveredURL(
                        source_id=self.source.id,
                        url=url,
                        url_path=url.replace(self.source.base_url, ""),
                        relevance=RelevanceStatus.RELEVANT if is_relevant else RelevanceStatus.NOT_RELEVANT,
                        relevance_score=result.get("confidence", 0) * 100,
                        relevance_reason=result.get("reason", ""),
                        status=URLStatus.CLASSIFIED,
                        discovered_at=datetime.utcnow(),
                        last_classified_at=datetime.utcnow()
                    )
                    self.db.add(discovered)

                if is_relevant:
                    relevant_urls.append(url)

            self.db.commit()

        self.job.urls_relevant = len(relevant_urls)
        self.db.commit()

        print(f"[Scrape] Found {len(relevant_urls)} relevant URLs")
        return relevant_urls

    async def _scrape_urls(self, urls: List[str]) -> List[DiscoveredURL]:
        """Scrape content for relevant URLs"""
        results = await self.firecrawl.scrape_urls_batch(urls, concurrency=5)

        self.job.firecrawl_calls += len(urls)
        scraped_urls = []

        for result in results:
            # Get the discovered URL record
            discovered = self.db.query(DiscoveredURL).filter(
                DiscoveredURL.source_id == self.source.id,
                DiscoveredURL.url == result.url
            ).first()

            if discovered:
                if result.success:
                    discovered.raw_markdown = result.markdown
                    discovered.content_hash = hashlib.md5(result.markdown.encode()).hexdigest()
                    discovered.status = URLStatus.SCRAPED
                    discovered.last_scraped_at = datetime.utcnow()
                    scraped_urls.append(discovered)
                else:
                    discovered.status = URLStatus.ERROR
                    discovered.error_message = result.error

        self.job.urls_scraped = len(scraped_urls)
        self.db.commit()

        return scraped_urls

    async def _classify_content(self, urls: List[DiscoveredURL]):
        """Classify scraped content"""
        ai_provider = get_ai_provider(self.db, TaskType.CONTENT_CLASSIFICATION)
        # Handle both enum and string values from database
        target_types = [t.value if hasattr(t, 'value') else t for t in self.source.target_item_types]

        for discovered in urls:
            if not discovered.raw_markdown:
                continue

            result = await ai_provider.classify_content(
                discovered.raw_markdown,
                discovered.url,
                target_types
            )

            # Update discovered URL with classification
            discovered.page_type = result.page_type
            discovered.detected_item_types = [ItemType(t) for t in result.detected_item_types] if result.detected_item_types else []
            discovered.content_tags = result.content_tags
            discovered.priority = PriorityLevel(result.priority) if result.priority else PriorityLevel.MEDIUM
            discovered.has_multiple_items = result.has_multiple_items
            discovered.status = URLStatus.CLASSIFIED

            # Log AI usage
            ai_log = AILog(
                task_type="CLASSIFY_CONTENT",
                model_used=ai_provider.model,
                provider=ai_provider.provider_name,
                job_id=self.job.id,
                related_type="discovered_url",
                related_id=discovered.id,
                input_tokens=len(discovered.raw_markdown),
                output_tokens=500,  # estimate
                created_at=datetime.utcnow()
            )
            self.db.add(ai_log)

        self.db.commit()

    async def _extract_data(self, urls: List[DiscoveredURL]):
        """Extract structured data from classified URLs"""
        ai_provider = get_ai_provider(self.db, TaskType.EXTRACTION)

        for discovered in urls:
            if not discovered.raw_markdown or not discovered.detected_item_types:
                continue

            # Extract for each detected item type
            for item_type in discovered.detected_item_types:
                # Get schema for this item type
                schema = self.db.query(ItemSchema).filter(
                    ItemSchema.item_type == item_type,
                    ItemSchema.is_active == True
                ).first()

                if not schema:
                    continue

                # Handle both enum and string values from database
                item_type_value = item_type.value if hasattr(item_type, 'value') else item_type

                result = await ai_provider.extract_data(
                    discovered.raw_markdown,
                    schema.schema_json,
                    item_type_value
                )

                if result.data:
                    # Create or update item
                    item = Item(
                        source_id=self.source.id,
                        discovered_url_id=discovered.id,
                        item_type=ItemType(item_type_value),
                        data=result.data,
                        field_status=result.field_status,
                        extraction_confidence=result.confidence * 100,
                        status=ItemStatus.NEEDS_REVIEW if result.confidence < 0.7 else ItemStatus.DRAFT,
                        extracted_at=datetime.utcnow()
                    )
                    self.db.add(item)
                    self.job.items_extracted += 1

                    # Log AI usage
                    ai_log = AILog(
                        task_type="EXTRACT",
                        model_used=ai_provider.model,
                        provider=ai_provider.provider_name,
                        job_id=self.job.id,
                        related_type="item",
                        input_tokens=len(discovered.raw_markdown),
                        output_tokens=1000,  # estimate
                        created_at=datetime.utcnow()
                    )
                    self.db.add(ai_log)

            discovered.status = URLStatus.EXTRACTED

        self.db.commit()
