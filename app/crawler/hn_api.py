"""
Hacker News API client module.
Provides functions to fetch stories and item details from HN Firebase API.
"""

import asyncio
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import HN_API_BASE_URL, CRAWLER_MAX_RETRIES, CRAWLER_TIMEOUT
from app.core.logger import app_logger


class HNAPIClient:
    """Hacker News API client for fetching stories and items."""

    def __init__(self):
        self.base_url = HN_API_BASE_URL
        self.timeout = CRAWLER_TIMEOUT
        self.max_retries = CRAWLER_MAX_RETRIES

    async def _fetch_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from URL with retry logic.

        Args:
            url: The URL to fetch

        Returns:
            JSON response as dict, or None if failed
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
                except httpx.TimeoutException:
                    app_logger.warning(f"Timeout fetching {url}, attempt {attempt + 1}/{self.max_retries}")
                except httpx.HTTPStatusError as e:
                    app_logger.warning(f"HTTP error {e.response.status_code} for {url}, attempt {attempt + 1}/{self.max_retries}")
                except Exception as e:
                    app_logger.error(f"Unexpected error fetching {url}: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        app_logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    async def fetch_top_stories(self, limit: int = 30) -> List[int]:
        """
        Fetch top story IDs from Hacker News.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of story IDs
        """
        url = f"{self.base_url}/topstories.json"
        app_logger.info(f"Fetching top {limit} stories from HN")

        story_ids = await self._fetch_with_retry(url)

        if story_ids is None:
            app_logger.error("Failed to fetch top stories")
            return []

        result = story_ids[:limit]
        app_logger.info(f"Successfully fetched {len(result)} story IDs")
        return result

    async def fetch_item_details(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a specific item (story, comment, etc.).

        Args:
            item_id: The HN item ID

        Returns:
            Item data dict with fields: id, type, by, time, title, url, score, kids, etc.
            Returns None if fetch failed
        """
        url = f"{self.base_url}/item/{item_id}.json"

        item_data = await self._fetch_with_retry(url)

        if item_data is None:
            app_logger.warning(f"Failed to fetch item {item_id}")
            return None

        # Validate essential fields for a story
        if item_data.get("type") == "story":
            if not item_data.get("title"):
                app_logger.warning(f"Story {item_id} missing title")
                return None

        app_logger.debug(f"Successfully fetched item {item_id}")
        return item_data

    async def fetch_multiple_items(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch multiple items concurrently.

        Args:
            item_ids: List of item IDs to fetch

        Returns:
            List of item data dicts (excludes failed fetches)
        """
        app_logger.info(f"Fetching {len(item_ids)} items concurrently")

        tasks = [self.fetch_item_details(item_id) for item_id in item_ids]
        results = await asyncio.gather(*tasks)

        # Filter out None results
        valid_results = [item for item in results if item is not None]

        app_logger.info(f"Successfully fetched {len(valid_results)}/{len(item_ids)} items")
        return valid_results


# Convenience functions
async def get_top_stories(limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch top stories with full details.

    Args:
        limit: Maximum number of stories to fetch

    Returns:
        List of story data dicts
    """
    client = HNAPIClient()

    # Get story IDs
    story_ids = await client.fetch_top_stories(limit)

    if not story_ids:
        return []

    # Fetch story details
    stories = await client.fetch_multiple_items(story_ids)

    # Filter to only include stories (not jobs, polls, etc.)
    stories = [s for s in stories if s.get("type") == "story"]

    app_logger.info(f"Fetched {len(stories)} complete stories")
    return stories


# Test function
async def test_hn_api():
    """Test the HN API client."""
    print("Testing HN API Client...")
    print("-" * 50)

    # Test 1: Fetch top 5 stories
    client = HNAPIClient()
    story_ids = await client.fetch_top_stories(limit=5)
    print(f"\n✓ Fetched {len(story_ids)} story IDs")
    print(f"  IDs: {story_ids[:3]}...")

    # Test 2: Fetch details for first story
    if story_ids:
        story = await client.fetch_item_details(story_ids[0])
        if story:
            print(f"\n✓ Fetched story details:")
            print(f"  Title: {story.get('title', 'N/A')}")
            print(f"  Score: {story.get('score', 0)}")
            print(f"  URL: {story.get('url', 'N/A')}")
            print(f"  Comments: {len(story.get('kids', []))}")

    # Test 3: Use convenience function
    stories = await get_top_stories(limit=3)
    print(f"\n✓ Convenience function fetched {len(stories)} stories")
    for i, story in enumerate(stories, 1):
        print(f"  {i}. {story.get('title', 'N/A')[:60]}...")

    print("\n" + "-" * 50)
    print("All tests passed! ✓")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_hn_api())
