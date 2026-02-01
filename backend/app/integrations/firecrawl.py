import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.config import settings
import asyncio


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


class FirecrawlClient:
    """Client for Firecrawl API"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.base_url = base_url or settings.FIRECRAWL_BASE_URL
        self.use_mock = not self.api_key or self.api_key == "mock"

    async def map_domain(self, url: str, limit: int = 1000) -> MapResult:
        """
        Get all URLs from a domain.
        Returns a list of discovered URLs.
        """
        if self.use_mock:
            return self._mock_map_domain(url)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/map",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "url": url,
                        "limit": limit
                    }
                )

                if response.status_code != 200:
                    return MapResult(
                        success=False,
                        urls=[],
                        error=f"API error: {response.status_code} - {response.text}"
                    )

                data = response.json()
                return MapResult(
                    success=True,
                    urls=data.get("links", [])
                )

        except Exception as e:
            return MapResult(
                success=False,
                urls=[],
                error=str(e)
            )

    async def scrape_url(self, url: str) -> ScrapeResult:
        """
        Scrape a single URL and return markdown content.
        """
        if self.use_mock:
            return self._mock_scrape_url(url)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/scrape",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "url": url,
                        "formats": ["markdown"]
                    }
                )

                if response.status_code != 200:
                    return ScrapeResult(
                        success=False,
                        url=url,
                        error=f"API error: {response.status_code}"
                    )

                data = response.json()
                return ScrapeResult(
                    success=True,
                    url=url,
                    markdown=data.get("data", {}).get("markdown", ""),
                    title=data.get("data", {}).get("metadata", {}).get("title")
                )

        except Exception as e:
            return ScrapeResult(
                success=False,
                url=url,
                error=str(e)
            )

    async def scrape_urls_batch(self, urls: List[str], concurrency: int = 5) -> List[ScrapeResult]:
        """
        Scrape multiple URLs with concurrency control.
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def scrape_with_semaphore(url: str) -> ScrapeResult:
            async with semaphore:
                result = await self.scrape_url(url)
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                return result

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    def _mock_map_domain(self, url: str) -> MapResult:
        """Return mock data for testing"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        # Generate mock URLs based on domain
        mock_urls = [
            f"https://{domain}/",
            f"https://{domain}/admissions",
            f"https://{domain}/admissions/graduate",
            f"https://{domain}/admissions/graduate/programs",
            f"https://{domain}/admissions/graduate/requirements",
            f"https://{domain}/admissions/graduate/deadlines",
            f"https://{domain}/programs/masters",
            f"https://{domain}/programs/masters/computer-science",
            f"https://{domain}/programs/masters/data-science",
            f"https://{domain}/programs/masters/artificial-intelligence",
            f"https://{domain}/programs/phd",
            f"https://{domain}/financial-aid",
            f"https://{domain}/financial-aid/scholarships",
            f"https://{domain}/financial-aid/fellowships",
            f"https://{domain}/international",
            f"https://{domain}/international/exchange-programs",
            f"https://{domain}/research",
            f"https://{domain}/faculty",
            f"https://{domain}/news",
            f"https://{domain}/events",
            f"https://{domain}/about",
            f"https://{domain}/contact",
            f"https://{domain}/login",
        ]

        return MapResult(success=True, urls=mock_urls)

    def _mock_scrape_url(self, url: str) -> ScrapeResult:
        """Return mock content for testing"""

        # Generate different content based on URL pattern
        if "computer-science" in url:
            content = """
# Master of Science in Computer Science

## Program Overview
The MS in Computer Science program prepares students for careers in software development, research, and technology leadership.

## Requirements
- Bachelor's degree in Computer Science or related field
- Minimum GPA: 3.0
- GRE scores (optional for 2024)
- TOEFL: 90+ or IELTS: 7.0+

## Duration
2 years (4 semesters) full-time

## Tuition
$55,000 per year for domestic students
$65,000 per year for international students

## Application Deadlines
- Fall admission: January 15
- Spring admission: September 1

## Curriculum
Core courses include:
- Advanced Algorithms
- Machine Learning
- Distributed Systems
- Software Engineering

## Financial Aid
Teaching and Research assistantships available.
Merit-based scholarships for exceptional candidates.

[Apply Now](https://example.edu/apply)
"""
        elif "scholarship" in url:
            content = """
# Graduate Scholarships

## Merit Scholarship
- Amount: $20,000 per year
- Duration: 2 years
- Eligibility: GPA 3.5+, strong research potential
- Deadline: February 1

## International Student Award
- Amount: $15,000 per year
- Eligibility: International students with demonstrated need
- Covers: Partial tuition
- Deadline: March 15

## Research Fellowship
- Amount: Full tuition + $30,000 stipend
- Duration: 4 years (PhD students)
- Requirements: Research proposal, faculty recommendation
- Deadline: December 15

## Application Process
1. Submit online application
2. Provide transcripts
3. Submit statement of purpose
4. Two letters of recommendation

[Apply for Scholarships](https://example.edu/financial-aid/apply)
"""
        elif "exchange" in url:
            content = """
# International Exchange Programs

## Erasmus+ Partnership
- Partner universities in 15 European countries
- Duration: 1-2 semesters
- Benefits: Tuition waiver at host institution, travel grant
- Eligibility: GPA 3.0+, completed 2 semesters

## Bilateral Exchange - Asia
- Partners: University of Tokyo, NUS Singapore, Tsinghua
- Duration: 1 semester
- Language: English-taught programs available
- Deadline: October 1 for Spring, March 1 for Fall

## Summer Programs
- Duration: 6-8 weeks
- Locations: UK, Germany, Australia
- Credits: 6-9 transferable credits
- Cost: $5,000-8,000 (includes housing)

## Application Requirements
- Current enrollment in good standing
- Personal statement
- Faculty recommendation
- Language proficiency (if applicable)

[Explore Programs](https://example.edu/international/programs)
"""
        elif "conference" in url or "events" in url:
            content = """
# Academic Conferences

## International Conference on Machine Learning (ICML 2025)
- Dates: July 15-20, 2025
- Location: Vienna, Austria
- Submission Deadline: February 1, 2025
- Registration Fee: $800 (students: $400)
- Topics: Deep Learning, Reinforcement Learning, NLP

## ACM SIGCHI Conference 2025
- Dates: April 25-30, 2025
- Location: San Francisco, CA
- Paper Deadline: September 15, 2024
- Registration: $650
- Focus: Human-Computer Interaction

## IEEE Data Science Conference
- Dates: October 10-12, 2025
- Location: Virtual + Singapore
- Abstract Deadline: May 1, 2025
- Student Registration: $200

[View All Conferences](https://example.edu/research/conferences)
"""
        else:
            content = """
# Graduate Programs

Welcome to our Graduate School. We offer world-class programs in:

- Computer Science
- Data Science
- Artificial Intelligence
- Business Administration
- Engineering

## Why Choose Us?
- Top 50 globally ranked
- Industry partnerships
- Research opportunities
- Career support

## Quick Links
- [Admissions](https://example.edu/admissions)
- [Programs](https://example.edu/programs)
- [Financial Aid](https://example.edu/financial-aid)
- [Contact](https://example.edu/contact)

## Upcoming Deadlines
- Fall 2025: January 15, 2025
- Spring 2025: September 1, 2024

Visit our campus or join a virtual info session!
"""

        return ScrapeResult(
            success=True,
            url=url,
            markdown=content.strip(),
            title=f"Page: {url.split('/')[-1]}"
        )
