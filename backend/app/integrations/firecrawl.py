"""
Firecrawl Client - Production integration with Firecrawl VM.

Supports:
- Dynamic VM IP lookup via GCP Compute API
- Crawl endpoint (async job-based scraping)
- Scrape endpoint (single URL)
- Map endpoint (URL discovery)
- Retry logic for transient failures
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.config import settings


@dataclass
class MapResult:
    """Result from mapping a domain"""
    success: bool
    urls: List[str]
    error: Optional[str] = None


@dataclass
class ScrapeResult:
    """Result from scraping a URL"""
    success: bool
    url: str
    markdown: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CrawlResult:
    """Result from a crawl job"""
    success: bool
    job_id: Optional[str] = None
    status: Optional[str] = None  # "scraping", "completed", "failed"
    total: int = 0
    completed: int = 0
    pages: List[ScrapeResult] = field(default_factory=list)
    error: Optional[str] = None
    next_url: Optional[str] = None


class FirecrawlClient:
    """Client for Firecrawl API with dynamic VM IP support"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.use_mock = self.api_key == "mock"

        # Cache the base URL to avoid repeated lookups
        if base_url:
            self._cached_base_url = base_url
        else:
            self._cached_base_url = self._resolve_base_url()

    def _resolve_base_url(self) -> str:
        """Resolve and cache base URL once"""
        # First try environment variable (most reliable)
        import os
        vm_ip = os.environ.get("FIRECRAWL_VM_IP")
        if vm_ip:
            return f"http://{vm_ip}:3002"

        # Use config setting
        if settings.FIRECRAWL_BASE_URL and "localhost" not in settings.FIRECRAWL_BASE_URL:
            return settings.FIRECRAWL_BASE_URL

        # Try dynamic VM service as last resort
        try:
            from app.services.vm_service import VMService
            return VMService.get_firecrawl_base_url()
        except Exception as e:
            print(f"[Firecrawl] Error getting VM IP: {e}")
            return settings.FIRECRAWL_BASE_URL

    @property
    def base_url(self) -> str:
        """Get cached base URL"""
        return self._cached_base_url

    def _headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ---------------------------------------------------------------
    # CRAWL — Async job-based scraping (primary method for production)
    # ---------------------------------------------------------------
    async def start_crawl(
        self,
        url: str,
        limit: int = 100,
        wait_for: int = 10000,
        max_depth: int = 7,
        include_paths: List[str] = None,
        exclude_paths: List[str] = None,
        scrape_options: Dict[str, Any] = None,
    ) -> CrawlResult:
        """
        Start an async crawl job.

        Args:
            url: The URL to start crawling from
            limit: Maximum number of pages to crawl
            wait_for: Time to wait for page load in ms
            max_depth: Maximum crawl depth from start URL
            include_paths: URL path patterns to include (e.g. ["/scholarship/", "/master/"])
            exclude_paths: URL path patterns to exclude (e.g. ["/login", "/cart"])
            scrape_options: Additional scrape options

        Returns:
            CrawlResult with job_id for polling
        """
        if self.use_mock:
            return CrawlResult(
                success=True,
                job_id="mock-crawl-job",
                status="completed",
            )

        payload = {
            "url": url,
            "limit": limit,
            "maxDepth": max_depth,
            "scrapeOptions": scrape_options or {
                "formats": ["markdown"],
                "waitFor": wait_for,
            },
        }

        if include_paths:
            payload["includePaths"] = include_paths
        if exclude_paths:
            payload["excludePaths"] = exclude_paths

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/crawl",
                    headers=self._headers(),
                    json=payload
                )

                if response.status_code not in (200, 201):
                    return CrawlResult(
                        success=False,
                        error=f"Crawl start failed: {response.status_code} - {response.text}"
                    )

                data = response.json()
                return CrawlResult(
                    success=True,
                    job_id=data.get("id") or data.get("jobId"),
                    status="scraping",
                )

        except Exception as e:
            return CrawlResult(success=False, error=str(e))

    async def get_crawl_status(self, job_id: str, retries: int = 3) -> CrawlResult:
        """Poll a crawl job for its current status and results with retry"""
        last_error = None

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                ) as client:
                    response = await client.get(
                        f"{self.base_url}/v1/crawl/{job_id}",
                        headers=self._headers(),
                    )

                    if response.status_code != 200:
                        return CrawlResult(
                            success=False,
                            error=f"Status check failed: {response.status_code}"
                        )

                    data = response.json()
                    status = data.get("status", "unknown")
                    pages = []

                    for page_data in data.get("data", []):
                        md = page_data.get("markdown", "")
                        meta = page_data.get("metadata", {})
                        url = meta.get("sourceURL") or meta.get("url", "")
                        title = meta.get("title", "")
                        pages.append(ScrapeResult(
                            success=True,
                            url=url,
                            markdown=md,
                            title=title,
                        ))

                    return CrawlResult(
                        success=True,
                        job_id=job_id,
                        status=status,
                        total=data.get("total", 0),
                        completed=data.get("completed", 0),
                        pages=pages,
                        next_url=data.get("next") or data.get("nextURL"),
                    )

            except Exception as e:
                last_error = str(e)
                if attempt < retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
                continue

        return CrawlResult(success=False, error=last_error)

    async def poll_crawl_until_done(
        self,
        job_id: str,
        poll_interval: int = 10,
        max_wait: int = 3600,
        on_progress=None,
    ) -> CrawlResult:
        """
        Poll a crawl job until completion.

        Args:
            job_id: The crawl job ID
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait
            on_progress: Optional callback(completed, total)

        Returns:
            Final CrawlResult with all pages
        """
        elapsed = 0
        all_pages = []
        seen_urls = set()

        while elapsed < max_wait:
            result = await self.get_crawl_status(job_id)

            if not result.success:
                return result

            # Collect new pages (dedupe by URL)
            for page in result.pages:
                normalized = (page.url or "").rstrip("/")
                if normalized and normalized not in seen_urls:
                    seen_urls.add(normalized)
                    all_pages.append(page)

            if on_progress:
                await on_progress(result.completed, result.total)

            if result.status == "completed":
                # Handle pagination if present
                if result.next_url:
                    await self._fetch_pagination(result.next_url, all_pages, seen_urls)

                return CrawlResult(
                    success=True,
                    job_id=job_id,
                    status="completed",
                    total=result.total,
                    completed=len(all_pages),
                    pages=all_pages,
                )

            elif result.status == "failed":
                return CrawlResult(
                    success=False,
                    job_id=job_id,
                    status="failed",
                    error="Crawl job failed",
                    pages=all_pages,
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return CrawlResult(
            success=True,
            job_id=job_id,
            status="timeout",
            total=result.total if result else 0,
            completed=len(all_pages),
            pages=all_pages,
        )

    async def _fetch_pagination(
        self,
        next_url: str,
        all_pages: List[ScrapeResult],
        seen_urls: set
    ):
        """Fetch additional pages from pagination URL"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                while next_url:
                    response = await client.get(next_url, headers=self._headers())
                    if response.status_code != 200:
                        break

                    data = response.json()
                    next_url = data.get("next") or data.get("nextURL")

                    for page_data in data.get("data", []):
                        md = page_data.get("markdown", "")
                        meta = page_data.get("metadata", {})
                        url = meta.get("sourceURL") or meta.get("url", "")

                        normalized = url.rstrip("/")
                        if normalized and normalized not in seen_urls:
                            seen_urls.add(normalized)
                            all_pages.append(ScrapeResult(
                                success=True,
                                url=url,
                                markdown=md,
                                title=meta.get("title", ""),
                            ))

                    await asyncio.sleep(1)  # Polite delay

        except Exception as e:
            print(f"[Firecrawl] Pagination error: {e}")

    # ---------------------------------------------------------------
    # MAP — URL discovery via sitemap
    # ---------------------------------------------------------------
    async def map_domain(self, url: str, limit: int = 100000) -> MapResult:
        """Get all URLs from a domain via sitemap"""
        if self.use_mock:
            return self._mock_map_domain(url)

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/map",
                    headers=self._headers(),
                    json={"url": url, "limit": limit}
                )

                if response.status_code != 200:
                    return MapResult(
                        success=False,
                        urls=[],
                        error=f"API error: {response.status_code} - {response.text}"
                    )

                data = response.json()
                return MapResult(success=True, urls=data.get("links", []))

        except Exception as e:
            return MapResult(success=False, urls=[], error=str(e))

    # ---------------------------------------------------------------
    # SCRAPE — Single URL scraping
    # ---------------------------------------------------------------
    async def scrape_url(
        self,
        url: str,
        wait_for: int = 5000,
        actions: List[Dict[str, Any]] = None,
    ) -> ScrapeResult:
        """Scrape a single URL and return markdown content"""
        if self.use_mock:
            return self._mock_scrape_url(url)

        try:
            payload = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": False,
                "waitFor": wait_for,
            }

            if actions:
                payload["actions"] = actions

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/scrape",
                    headers=self._headers(),
                    json=payload
                )

                if response.status_code != 200:
                    return ScrapeResult(
                        success=False,
                        url=url,
                        error=f"API error: {response.status_code} - {response.text}"
                    )

                data = response.json()
                return ScrapeResult(
                    success=True,
                    url=url,
                    markdown=data.get("data", {}).get("markdown", ""),
                    title=data.get("data", {}).get("metadata", {}).get("title")
                )

        except Exception as e:
            return ScrapeResult(success=False, url=url, error=str(e))

    async def scrape_urls_batch(
        self,
        urls: List[str],
        concurrency: int = 5,
    ) -> List[ScrapeResult]:
        """Scrape multiple URLs with concurrency control"""
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str) -> ScrapeResult:
            async with semaphore:
                result = await self.scrape_url(url)
                await asyncio.sleep(0.5)
                return result

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    # ---------------------------------------------------------------
    # MOCK implementations
    # ---------------------------------------------------------------
    def _mock_map_domain(self, url: str) -> MapResult:
        """Return mock data for testing"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

        mock_urls = [
            f"https://{domain}/",
            f"https://{domain}/admissions/graduate",
            f"https://{domain}/programs/masters/computer-science",
            f"https://{domain}/programs/masters/data-science",
            f"https://{domain}/programs/phd",
            f"https://{domain}/financial-aid/scholarships",
            f"https://{domain}/international/exchange-programs",
        ]
        return MapResult(success=True, urls=mock_urls)

    def _mock_scrape_url(self, url: str) -> ScrapeResult:
        """Return mock content for testing"""
        content = f"""
# Sample Program Page

## Program Overview
This is a sample program from {url}.

## Key Information
- Name: Sample Graduate Program
- Country: United States
- Summary: A comprehensive graduate program.

## Apply Now
Visit the website for more information.
"""
        return ScrapeResult(
            success=True,
            url=url,
            markdown=content.strip(),
            title=f"Page: {url.split('/')[-1]}"
        )
