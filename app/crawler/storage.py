"""
Data storage module.
Handles persistence of crawled articles with configurable storage strategies.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from app.core.config import PROJECT_ROOT
from app.core.logger import app_logger


# Storage paths
DATA_DIR = PROJECT_ROOT / "data"
METADATA_FILE = DATA_DIR / "articles.json"
CRAWLED_IDS_FILE = DATA_DIR / "crawled_ids.json"
FAILED_ITEMS_FILE = DATA_DIR / "failed_items.json"

# Content truncation settings
CONTENT_SUMMARY_LENGTH = 2000  # 保存前 2000 字符


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_crawled_ids() -> Set[int]:
    """
    Load set of already crawled item IDs.

    Returns:
        Set of item IDs that have been crawled
    """
    ensure_data_dir()

    if not CRAWLED_IDS_FILE.exists():
        return set()

    try:
        with open(CRAWLED_IDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    except Exception as e:
        app_logger.error(f"Error loading crawled IDs: {e}")
        return set()


def save_crawled_ids(ids: Set[int]):
    """
    Save set of crawled item IDs.

    Args:
        ids: Set of item IDs
    """
    ensure_data_dir()

    try:
        with open(CRAWLED_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "ids": list(ids),
                "updated_at": datetime.now().isoformat()
            }, f)
        app_logger.debug(f"Saved {len(ids)} crawled IDs")
    except Exception as e:
        app_logger.error(f"Error saving crawled IDs: {e}")


def prepare_article_for_storage(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare article data for storage (truncate content, add metadata).

    Args:
        article: Full article dict from crawler

    Returns:
        Trimmed article dict for storage
    """
    content = article.get("content", "")

    stored = {
        # Core identifiers
        "item_id": article.get("id"),
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "author": article.get("by", ""),

        # Metrics
        "score": article.get("score", 0),
        "descendants": article.get("descendants", 0),  # Total comment count

        # Timestamps
        "timestamp": article.get("time", 0),
        "crawl_date": datetime.now().strftime("%Y-%m-%d"),
        "crawl_time": datetime.now().isoformat(),

        # Content (truncated)
        "content_type": article.get("content_type", "unknown"),
        "content_length": len(content) if content else 0,
        "content_summary": content[:CONTENT_SUMMARY_LENGTH] if content else None,

        # Comments
        "comments_summary": article.get("comments_summary", ""),
        "top_comments": article.get("top_comments", []),
        "comment_count": article.get("comment_count", 0),

        # Classification (if available)
        "topic": article.get("topic"),
        "tags": article.get("tags", []),
        "classification_confidence": article.get("classification_confidence"),
    }

    return stored


def load_articles() -> List[Dict[str, Any]]:
    """
    Load all stored articles.

    Returns:
        List of article dicts
    """
    ensure_data_dir()

    if not METADATA_FILE.exists():
        return []

    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("articles", [])
    except Exception as e:
        app_logger.error(f"Error loading articles: {e}")
        return []


def save_articles(articles: List[Dict[str, Any]], append: bool = True):
    """
    Save articles to storage.

    Args:
        articles: List of article dicts (already prepared for storage)
        append: If True, append to existing articles; if False, replace
    """
    ensure_data_dir()

    if append:
        existing = load_articles()
        existing_ids = {a["item_id"] for a in existing}

        # Only add new articles
        new_articles = [a for a in articles if a["item_id"] not in existing_ids]
        all_articles = existing + new_articles

        app_logger.info(f"Appending {len(new_articles)} new articles (total: {len(all_articles)})")
    else:
        all_articles = articles
        app_logger.info(f"Saving {len(all_articles)} articles (replace mode)")

    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "articles": all_articles,
                "count": len(all_articles),
                "updated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        app_logger.info(f"Saved {len(all_articles)} articles to {METADATA_FILE}")

        # Update crawled IDs
        crawled_ids = load_crawled_ids()
        crawled_ids.update(a["item_id"] for a in articles)
        save_crawled_ids(crawled_ids)

    except Exception as e:
        app_logger.error(f"Error saving articles: {e}")
        raise


def save_failed_items(failed_items: List[Dict[str, Any]]):
    """
    Save failed crawl items for later retry.

    Args:
        failed_items: List of failed item info
    """
    ensure_data_dir()

    try:
        # Load existing
        existing = []
        if FAILED_ITEMS_FILE.exists():
            with open(FAILED_ITEMS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing = data.get("items", [])

        # Append new failures
        all_failed = existing + failed_items

        with open(FAILED_ITEMS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "items": all_failed,
                "count": len(all_failed),
                "updated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        app_logger.info(f"Saved {len(failed_items)} failed items")

    except Exception as e:
        app_logger.error(f"Error saving failed items: {e}")


def get_storage_stats() -> Dict[str, Any]:
    """
    Get statistics about stored data.

    Returns:
        Dict with storage statistics
    """
    articles = load_articles()
    crawled_ids = load_crawled_ids()

    return {
        "total_articles": len(articles),
        "total_crawled_ids": len(crawled_ids),
        "metadata_file": str(METADATA_FILE),
        "file_exists": METADATA_FILE.exists(),
        "file_size_kb": METADATA_FILE.stat().st_size / 1024 if METADATA_FILE.exists() else 0
    }


# Test function
def test_storage():
    """Test storage functions."""
    print("Testing Storage Module...")
    print("-" * 50)

    # Test data
    test_article = {
        "id": 99999999,
        "title": "Test Article for Storage",
        "url": "https://example.com/test",
        "by": "test_user",
        "score": 100,
        "time": 1732287600,
        "descendants": 50,
        "content": "A" * 5000,  # 5000 chars, will be truncated
        "content_type": "article",
        "comments_summary": "Test comment summary...",
        "top_comments": [{"author": "user1", "text": "Great!", "score": 25}],
        "comment_count": 5
    }

    # Prepare for storage
    print("\n1. Preparing article for storage...")
    prepared = prepare_article_for_storage(test_article)
    print(f"   Original content length: 5000")
    print(f"   Stored content_length: {prepared['content_length']}")
    print(f"   Stored content_summary length: {len(prepared['content_summary'])}")
    print(f"   ✓ Content truncated to {CONTENT_SUMMARY_LENGTH} chars")

    # Save
    print("\n2. Saving article...")
    save_articles([prepared], append=True)
    print(f"   ✓ Saved to {METADATA_FILE}")

    # Load
    print("\n3. Loading articles...")
    loaded = load_articles()
    print(f"   ✓ Loaded {len(loaded)} articles")

    # Stats
    print("\n4. Storage stats:")
    stats = get_storage_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "-" * 50)
    print("Storage tests complete! ✓")


if __name__ == "__main__":
    test_storage()
