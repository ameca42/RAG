"""
Integrated crawler module.
Orchestrates the complete crawl pipeline: fetch stories -> content -> comments -> classify -> save.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.crawler.hn_api import HNAPIClient, get_top_stories
from app.crawler.fetcher import ArticleFetcher, fetch_multiple_articles
from app.crawler.parser import CommentParser, parse_multiple_stories
from app.crawler.classifier import ArticleClassifier, classify_articles
from app.crawler.storage import (
    load_crawled_ids,
    save_articles,
    save_failed_items,
    prepare_article_for_storage,
    get_storage_stats
)
from app.core.config import CRAWLER_MAX_STORIES
from app.core.logger import app_logger


class HNCrawler:
    """
    Integrated Hacker News crawler.
    Fetches stories, content, comments, classifies and saves to storage.
    """

    def __init__(self, max_stories: int = None, enable_classification: bool = True):
        self.max_stories = max_stories or CRAWLER_MAX_STORIES
        self.enable_classification = enable_classification
        self.api_client = HNAPIClient()
        self.fetcher = ArticleFetcher()
        self.parser = CommentParser()
        self.classifier = ArticleClassifier() if enable_classification else None

        # Statistics
        self.stats = {
            "started_at": None,
            "finished_at": None,
            "total_fetched": 0,
            "new_articles": 0,
            "skipped_existing": 0,
            "content_success": 0,
            "content_failed": 0,
            "content_skipped": 0,
            "comments_parsed": 0,
            "classified": 0,
            "errors": []
        }

    async def crawl(self, skip_existing: bool = True) -> List[Dict[str, Any]]:
        """
        Run the complete crawl pipeline.

        Args:
            skip_existing: If True, skip already crawled stories

        Returns:
            List of crawled and processed articles
        """
        self.stats["started_at"] = datetime.now().isoformat()
        total_steps = 5 if self.enable_classification else 4
        app_logger.info(f"Starting crawl for top {self.max_stories} stories")

        # Step 1: Fetch story IDs
        app_logger.info(f"Step 1/{total_steps}: Fetching story IDs from HN...")
        story_ids = await self.api_client.fetch_top_stories(self.max_stories)

        if not story_ids:
            app_logger.error("Failed to fetch story IDs")
            return []

        # Step 2: Filter out existing stories
        if skip_existing:
            crawled_ids = load_crawled_ids()
            new_ids = [sid for sid in story_ids if sid not in crawled_ids]
            self.stats["skipped_existing"] = len(story_ids) - len(new_ids)

            if not new_ids:
                app_logger.info("No new stories to crawl")
                return []

            app_logger.info(f"Step 2/{total_steps}: Filtering - {len(new_ids)} new, {self.stats['skipped_existing']} existing")
            story_ids = new_ids
        else:
            app_logger.info(f"Step 2/{total_steps}: Skip filtering disabled, processing all stories")

        # Step 3: Fetch story details
        app_logger.info(f"Step 3/{total_steps}: Fetching {len(story_ids)} story details...")
        stories = await self.api_client.fetch_multiple_items(story_ids)
        stories = [s for s in stories if s.get("type") == "story"]
        self.stats["total_fetched"] = len(stories)

        if not stories:
            app_logger.warning("No valid stories found")
            return []

        # Step 4: Fetch content and parse comments
        app_logger.info(f"Step 4/{total_steps}: Fetching content and parsing comments for {len(stories)} stories...")

        # Fetch article content
        stories_with_content = await fetch_multiple_articles(stories)

        # Count content results
        for story in stories_with_content:
            ct = story.get("content_type", "unknown")
            if ct == "article" and story.get("content"):
                self.stats["content_success"] += 1
            elif ct == "failed":
                self.stats["content_failed"] += 1
            else:
                self.stats["content_skipped"] += 1

        # Parse comments
        stories_with_comments = await parse_multiple_stories(stories_with_content)
        self.stats["comments_parsed"] = sum(s.get("comment_count", 0) for s in stories_with_comments)

        # Step 5: Classify articles (optional)
        if self.enable_classification:
            app_logger.info(f"Step 5/{total_steps}: Classifying {len(stories_with_comments)} articles...")
            stories_classified = await classify_articles(stories_with_comments)
            self.stats["classified"] = len([s for s in stories_classified if s.get("topic")])
        else:
            stories_classified = stories_with_comments

        # Prepare for storage
        prepared_articles = [prepare_article_for_storage(s) for s in stories_classified]
        self.stats["new_articles"] = len(prepared_articles)

        # Save to storage
        app_logger.info(f"Saving {len(prepared_articles)} articles to storage...")
        save_articles(prepared_articles, append=True)

        # Save failed items
        failed_items = [
            {"item_id": s.get("id"), "title": s.get("title"), "url": s.get("url"), "error": "content_fetch_failed"}
            for s in stories_classified
            if s.get("content_type") == "failed"
        ]
        if failed_items:
            save_failed_items(failed_items)

        self.stats["finished_at"] = datetime.now().isoformat()

        # Log summary
        self._log_summary()

        return prepared_articles

    def _log_summary(self):
        """Log crawl summary."""
        app_logger.info("=" * 50)
        app_logger.info("CRAWL COMPLETE")
        app_logger.info("=" * 50)
        app_logger.info(f"Total fetched: {self.stats['total_fetched']}")
        app_logger.info(f"New articles saved: {self.stats['new_articles']}")
        app_logger.info(f"Skipped (existing): {self.stats['skipped_existing']}")
        app_logger.info(f"Content: {self.stats['content_success']} success, {self.stats['content_failed']} failed, {self.stats['content_skipped']} skipped")
        app_logger.info(f"Comments parsed: {self.stats['comments_parsed']}")
        app_logger.info("=" * 50)

    def get_stats(self) -> Dict[str, Any]:
        """Get crawl statistics."""
        return self.stats.copy()


async def crawl_top_stories(limit: int = None, skip_existing: bool = True) -> List[Dict[str, Any]]:
    """
    Convenience function to crawl top stories.

    Args:
        limit: Maximum number of stories to crawl
        skip_existing: Skip already crawled stories

    Returns:
        List of crawled articles
    """
    crawler = HNCrawler(max_stories=limit)
    return await crawler.crawl(skip_existing=skip_existing)


# CLI entry point
async def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Hacker News Crawler")
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of stories to crawl")
    parser.add_argument("--all", action="store_true", help="Crawl all, including existing")
    parser.add_argument("--stats", action="store_true", help="Show storage stats only")

    args = parser.parse_args()

    if args.stats:
        stats = get_storage_stats()
        print("\n📊 Storage Statistics:")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    print(f"\n🕷️  Starting HN Crawler...")
    print(f"   Target: Top {args.num} stories")
    print(f"   Skip existing: {not args.all}")
    print("-" * 40)

    crawler = HNCrawler(max_stories=args.num)
    articles = await crawler.crawl(skip_existing=not args.all)

    print(f"\n✅ Crawl complete!")
    print(f"   Saved {len(articles)} new articles")

    # Show sample
    if articles:
        print(f"\n📰 Sample articles:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. [{article['score']}] {article['title'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
