"""
Vector pipeline for processing articles and storing them in ChromaDB.

This module integrates:
- Document processing and splitting
- Vector embeddings generation
- ChromaDB storage with deduplication
"""

from typing import List, Dict, Any
from langchain_core.documents import Document
from app.db import VectorStoreManager
from app.chains.document_processor import DocumentProcessor
from app.core.logger import logger


class VectorPipeline:
    """Pipeline for processing articles into vectors and storing them."""

    def __init__(self, collection_name: str = "hn_articles"):
        """
        Initialize vector pipeline.

        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.vector_store = VectorStoreManager(collection_name)
        self.doc_processor = DocumentProcessor()

    def ingest_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a single article into the vector store (with deduplication).

        Args:
            article: Article dictionary from storage

        Returns:
            Dictionary with ingestion stats
        """
        item_id = article.get("item_id")
        title = article.get("title", "")

        if not item_id:
            logger.error("Article missing item_id, skipping ingestion")
            return {"error": "missing_item_id", "ingested": 0}

        # Check if article already exists in vector store
        if self.vector_store.check_exists(item_id, "article"):
            logger.info(f"Article {item_id} already exists in vector store, skipping")
            return {"status": "skipped", "ingested": 0, "item_id": item_id}

        try:
            # Process article into documents
            documents = self.doc_processor.process_article(article)

            if not documents:
                logger.warning(f"No documents created for article '{title[:50]}...'")
                return {"status": "no_documents", "ingested": 0, "item_id": item_id}

            # Add to vector store
            doc_ids = self.vector_store.add_documents(documents)

            logger.success(
                f"Successfully ingested article '{title[:50]}...' "
                f"({len(documents)} documents, {len(doc_ids)} IDs)"
            )

            return {
                "status": "success",
                "ingested": len(documents),
                "item_id": item_id,
                "doc_ids": doc_ids
            }

        except Exception as e:
            logger.error(f"Failed to ingest article {item_id}: {e}")
            return {"status": "error", "error": str(e), "ingested": 0, "item_id": item_id}

    def ingest_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest a batch of articles into the vector store.

        Args:
            articles: List of article dictionaries

        Returns:
            Dictionary with batch ingestion stats
        """
        if not articles:
            logger.warning("No articles to ingest")
            return {"total": 0, "ingested": 0, "skipped": 0, "errors": 0}

        stats = {
            "total": len(articles),
            "ingested": 0,
            "skipped": 0,
            "errors": 0,
            "docs_created": 0
        }

        logger.info(f"Starting batch ingestion of {len(articles)} articles")

        for article in articles:
            try:
                result = self.ingest_article(article)

                if result["status"] == "success":
                    stats["ingested"] += 1
                    stats["docs_created"] += result["ingested"]
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                stats["errors"] += 1
                continue

        logger.success(
            f"Batch ingestion complete: {stats['ingested']} ingested, "
            f"{stats['skipped']} skipped, {stats['errors']} errors, "
            f"{stats['docs_created']} docs created"
        )

        return stats

    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Dict[str, Any] = None
    ) -> List[Document]:
        """
        Search documents in the vector store.

        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of relevant documents
        """
        return self.vector_store.similarity_search(query, k, filter_dict)

    def search_by_topic(self, query: str, topic: str, k: int = 5) -> List[Document]:
        """
        Search within a specific topic.

        Args:
            query: Search query
            topic: Topic name (e.g., "AI/ML", "Security/Privacy")
            k: Number of results to return

        Returns:
            List of relevant documents
        """
        return self.search(query, k, {"topic": topic})

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return self.vector_store.get_collection_stats()
