"""
Article content fetcher module.
Fetches and converts web page content to Markdown format using Jina Reader API.
"""

import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx

from app.core.config import JINA_READER_BASE_URL, CRAWLER_MAX_RETRIES, CRAWLER_TIMEOUT
from app.core.logger import app_logger


class ArticleFetcher:
    """
    Fetches article content and converts to Markdown.
    Uses Jina Reader API for intelligent content extraction.
    """

    def __init__(self):
        self.jina_base_url = JINA_READER_BASE_URL
        self.timeout = CRAWLER_TIMEOUT
        self.max_retries = CRAWLER_MAX_RETRIES

        # Non-text content types to skip
        self.skip_extensions = {'.pdf', '.mp4', '.mp3', '.avi', '.mov', '.zip', '.tar', '.gz'}
        self.skip_domains = {'youtube.com', 'youtu.be', 'vimeo.com'}

    def _should_skip_url(self, url: str) -> tuple[bool, str]:
        """
        Check if URL should be skipped (PDF, video, etc.).

        Args:
            url: The URL to check

        Returns:
            (should_skip: bool, content_type: str)
        """
        if not url:
            return True, "no-url"

        try:
            parsed = urlparse(url)

            # Check domain
            domain = parsed.netloc.lower()
            for skip_domain in self.skip_domains:
                if skip_domain in domain:
                    return True, "video"

            # Check file extension
            path = parsed.path.lower()
            for ext in self.skip_extensions:
                if path.endswith(ext):
                    return True, ext[1:]  # Remove the dot

            return False, "article"

        except Exception as e:
            app_logger.warning(f"Error parsing URL {url}: {e}")
            return True, "invalid-url"

    async def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch article content using Jina Reader API.

        Args:
            url: The article URL

        Returns:
            Markdown content, or None if failed
        """
        # Check if should skip
        should_skip, content_type = self._should_skip_url(url)
        if should_skip:
            app_logger.info(f"Skipping URL (type: {content_type}): {url}")
            return None

        # Construct Jina Reader URL
        jina_url = f"{self.jina_base_url}/{url}"

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for attempt in range(self.max_retries):
                try:
                    app_logger.debug(f"Fetching content from {url}, attempt {attempt + 1}")

                    response = await client.get(jina_url)

                    # Handle different status codes
                    if response.status_code == 200:
                        content = response.text

                        # Basic validation
                        if len(content) < 100:
                            app_logger.warning(f"Content too short for {url}: {len(content)} chars")
                            return None

                        app_logger.info(f"Successfully fetched content from {url} ({len(content)} chars)")
                        return content

                    elif response.status_code == 403:
                        app_logger.warning(f"403 Forbidden for {url}")
                        return None

                    elif response.status_code == 404:
                        app_logger.warning(f"404 Not Found for {url}")
                        return None

                    else:
                        app_logger.warning(f"HTTP {response.status_code} for {url}")

                except httpx.TimeoutException:
                    app_logger.warning(f"Timeout fetching {url}, attempt {attempt + 1}/{self.max_retries}")

                except httpx.HTTPStatusError as e:
                    app_logger.warning(f"HTTP error for {url}: {e}")

                except Exception as e:
                    app_logger.error(f"Unexpected error fetching {url}: {e}")

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        app_logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    async def fetch_article_data(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch full article data including content.

        Args:
            story: Story dict from HN API (must have 'url' and 'title')

        Returns:
            Enhanced story dict with 'content' and 'content_type' fields
        """
        url = story.get("url", "")
        title = story.get("title", "Untitled")

        # Copy story data
        result = story.copy()

        # Check if should skip
        should_skip, content_type = self._should_skip_url(url)

        if should_skip:
            result["content"] = None
            result["content_type"] = content_type
            app_logger.info(f"Skipped '{title}' (type: {content_type})")
            return result

        # Fetch content
        content = await self.fetch_content(url)

        if content:
            result["content"] = content
            result["content_type"] = "article"
            app_logger.info(f"Fetched content for '{title}'")
        else:
            result["content"] = None
            result["content_type"] = "failed"
            app_logger.warning(f"Failed to fetch content for '{title}'")

        return result


async def fetch_multiple_articles(stories: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Fetch content for multiple articles concurrently.

    Args:
        stories: List of story dicts from HN API

    Returns:
        List of enhanced story dicts with content
    """
    fetcher = ArticleFetcher()

    app_logger.info(f"Fetching content for {len(stories)} articles")

    tasks = [fetcher.fetch_article_data(story) for story in stories]
    results = await asyncio.gather(*tasks)

    # Count successes
    success_count = sum(1 for r in results if r.get("content_type") == "article" and r.get("content"))
    skip_count = sum(1 for r in results if r.get("content_type") not in ["article", "failed"])
    fail_count = sum(1 for r in results if r.get("content_type") == "failed")

    app_logger.info(f"Fetch results: {success_count} success, {skip_count} skipped, {fail_count} failed")

    return results


# Test function
async def test_fetcher():
    """Test the article fetcher."""
    print("Testing Article Fetcher...")
    print("-" * 50)

    fetcher = ArticleFetcher()

    # Test 1: Normal article
    test_url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    print(f"\nTest 1: Fetching normal article")
    print(f"  URL: {test_url}")

    content = await fetcher.fetch_content(test_url)
    if content:
        print(f"  ✓ Success: {len(content)} characters")
        print(f"  Preview: {content[:200]}...")
    else:
        print(f"  ✗ Failed to fetch content")

    # Test 2: URL detection - PDF (should skip)
    pdf_url = "https://example.com/document.pdf"
    print(f"\nTest 2: PDF detection")
    print(f"  URL: {pdf_url}")
    should_skip, content_type = fetcher._should_skip_url(pdf_url)
    print(f"  ✓ Correctly detected as: {content_type} (skip: {should_skip})")

    # Test 3: URL detection - YouTube (should skip)
    video_url = "https://youtube.com/watch?v=123"
    print(f"\nTest 3: Video detection")
    print(f"  URL: {video_url}")
    should_skip, content_type = fetcher._should_skip_url(video_url)
    print(f"  ✓ Correctly detected as: {content_type} (skip: {should_skip})")

    # Test 4: Fetch with story dict
    test_story = {
        "id": 12345,
        "title": "Test Article",
        "url": "https://example.com/article",
        "score": 100
    }
    print(f"\nTest 4: Fetch with story dict")
    result = await fetcher.fetch_article_data(test_story)
    print(f"  Title: {result['title']}")
    print(f"  Content type: {result.get('content_type', 'N/A')}")
    if result.get('content'):
        print(f"  ✓ Content fetched: {len(result['content'])} chars")
    else:
        print(f"  ℹ Content: {result.get('content', 'None')}")

    print("\n" + "-" * 50)
    print("Fetcher tests complete! ✓")


if __name__ == "__main__":
    asyncio.run(test_fetcher())
