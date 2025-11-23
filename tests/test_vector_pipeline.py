#!/usr/bin/env python3
"""
Test script for vector pipeline - demonstrates document processing and retrieval.

Usage:
    python test_vector_pipeline.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chains.vector_pipeline import VectorPipeline
from app.crawler.storage import load_articles
from app.db.vector_store import VectorStoreManager
from app.core.logger import logger


def test_ingestion():
    """Test ingesting articles into vector store."""
    logger.info("=" * 60)
    logger.info("Testing Article Ingestion to Vector Store")
    logger.info("=" * 60)

    # Load articles from storage
    articles = load_articles()
    logger.info(f"Loaded {len(articles)} articles from storage")

    # Initialize pipeline
    pipeline = VectorPipeline(collection_name="hn_articles_test")

    # Ingest a few articles (first 2 for testing)
    test_articles = articles[:2]
    logger.info(f"Ingesting {len(test_articles)} articles...")

    stats = pipeline.ingest_batch(test_articles)

    logger.success(f"Ingestion stats: {stats}")
    return pipeline, stats


def test_search(pipeline):
    """Test semantic search functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Semantic Search")
    logger.info("=" * 60)

    # Test 1: General search
    logger.info("\n--- Test 1: General search on 'privacy and data protection' ---")
    results = pipeline.search("privacy and data protection", k=3)
    for i, doc in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"Result {i}:")
        print(f"{'='*60}")
        print(f"Title: {doc.metadata.get('title', 'N/A')}")
        print(f"Topic: {doc.metadata.get('topic', 'N/A')}")
        print(f"Score: {doc.metadata.get('score', 0)}")
        print(f"Type: {doc.metadata.get('doc_type', 'N/A')}")
        print(f"Content preview: {doc.page_content[:200]}...")

    # Test 2: Search by topic
    logger.info("\n--- Test 2: Search within 'Security/Privacy' topic ---")
    results = pipeline.search_by_topic("data breach consequences", topic="Security/Privacy", k=3)
    print(f"\nFound {len(results)} results in Security/Privacy topic\n")
    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc.metadata.get('title', 'N/A')[:60]}... (score: {doc.metadata.get('score', 0)})")

    # Test 3: Filtered search (document type)
    logger.info("\n--- Test 3: Search only in comments ---")
    results = pipeline.search(
        "privacy concerns",
        k=3,
        filter_dict={"doc_type": "comments"}
    )
    print(f"\nFound {len(results)} comment documents\n")
    for i, doc in enumerate(results, 1):
        print(f"{i}. Source: {doc.metadata.get('title', 'N/A')[:50]}...")
        print(f"   Type: {doc.metadata.get('chunk_type', 'full')}")
        print(f"   Preview: {doc.page_content[:150]}...")
        print()


def test_deduplication():
    """Test deduplication (ingesting same article twice)."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Deduplication")
    logger.info("=" * 60)

    articles = load_articles()
    pipeline = VectorPipeline(collection_name="hn_articles_test")

    # Try to ingest same article twice
    test_article = articles[0]
    item_id = test_article["item_id"]

    logger.info(f"First ingestion of article {item_id}...")
    result1 = pipeline.ingest_article(test_article)
    logger.info(f"Result: {result1}")

    logger.info(f"\nSecond ingestion of article {item_id} (should be skipped)...")
    result2 = pipeline.ingest_article(test_article)
    logger.info(f"Result: {result2}")


def test_stats():
    """Test collection statistics."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Collection Statistics")
    logger.info("=" * 60)

    pipeline = VectorStoreManager(collection_name="hn_articles_test")
    stats = pipeline.get_collection_stats()

    print(f"\nCollection Statistics:")
    print(json.dumps(stats, indent=2))


def main():
    """Run all tests."""
    try:
        # Test ingestion
        pipeline, stats = test_ingestion()

        # Show stats
        print(f"\n{'='*60}")
        print("INGESTION STATS")
        print(f"{'='*60}")
        print(json.dumps(stats, indent=2))

        # Test search
        test_search(pipeline)

        # Test deduplication
        test_deduplication()

        # Test stats
        test_stats()

        logger.success("\nAll tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
