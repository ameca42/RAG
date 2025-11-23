"""
Vector store management using ChromaDB.

This module handles:
- Document vectorization using OpenAI embeddings
- ChromaDB collection management
- Semantic search with metadata filtering
- Duplicate detection for incremental updates
"""

import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
import json
from app.core.config import OPENAI_API_KEY, OPENAI_BASE_URL, CHROMA_PERSIST_DIR, OPENAI_EMBEDDING_MODEL
from app.core.logger import logger
from datetime import datetime


class VectorStoreManager:
    """Manages vector storage operations using ChromaDB."""

    def __init__(self, collection_name: str = "hn_articles"):
        """
        Initialize vector store manager.

        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=OPENAI_EMBEDDING_MODEL,
            base_url=OPENAI_BASE_URL
        )

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Connected to existing collection '{collection_name}'")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection '{collection_name}'")

        # Initialize LangChain Chroma wrapper
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings
        )

    def _generate_doc_id(self, metadata: Dict[str, Any]) -> str:
        """
        Generate unique document ID from metadata.

        Args:
            metadata: Document metadata containing item_id, doc_type, etc.

        Returns:
            Unique document ID string

        Raises:
            ValueError: If metadata is missing required 'item_id' field
        """
        item_id = metadata.get("item_id")
        if not item_id:
            raise ValueError("Document metadata missing 'item_id'")

        doc_type = metadata.get("doc_type", "article")
        chunk_index = metadata.get("chunk_index")
        chunk_type = metadata.get("chunk_type")
        comment_index = metadata.get("comment_index")

        # Build ID parts based on available metadata
        parts = [str(item_id), doc_type]

        if chunk_index is not None:
            # Article or comment chunk with numeric index
            parts.append(str(chunk_index))
        elif chunk_type:
            # Comment with chunk_type (full, partial, top_comment)
            parts.append(chunk_type)
            if comment_index is not None:
                parts.append(str(comment_index))

        return "_".join(parts)

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to vector store.

        Args:
            documents: List of LangChain Document objects

        Returns:
            List of document IDs
        """
        if not documents:
            logger.warning("No documents to add")
            return []

        try:
            # Generate document IDs using the helper method
            doc_ids = []
            metadatas = []

            for doc in documents:
                try:
                    doc_id = self._generate_doc_id(doc.metadata)
                    doc_ids.append(doc_id)
                    metadatas.append(doc.metadata)
                except ValueError as e:
                    logger.warning(f"Skipping document with invalid metadata: {e}")
                    continue

            # Add documents to vector store
            if doc_ids:
                self.vectorstore.add_documents(
                    documents=documents[:len(doc_ids)],  # Only add docs with valid IDs
                    ids=doc_ids
                )

                logger.info(f"Successfully added {len(doc_ids)} documents to vector store")
            else:
                logger.warning("No valid documents to add")

            return doc_ids

        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}")
            raise

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search with optional metadata filtering.

        Args:
            query: Search query string
            k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"topic": "AI/ML"})

        Returns:
            List of relevant documents
        """
        try:
            # Validate query
            if not query or not query.strip():
                logger.warning("Empty search query received")
                raise ValueError("Search query cannot be empty")

            # Convert filter_dict to ChromaDB format (requires $and for multiple conditions)
            chroma_filter = None
            if filter_dict:
                if len(filter_dict) == 1:
                    # Single condition - use directly
                    chroma_filter = filter_dict
                else:
                    # Multiple conditions - use $and operator
                    chroma_filter = {
                        "$and": [
                            {key: value} for key, value in filter_dict.items()
                        ]
                    }

            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=chroma_filter
            )

            logger.info(f"Found {len(results)} relevant documents for query: {query}")

            if filter_dict:
                logger.debug(f"Applied filters: {filter_dict}")

            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

    def search_by_tags(
        self,
        query: str,
        tags: List[str],
        k: int = 5,
        match_all: bool = False
    ) -> List[Document]:
        """
        Search for documents with specific tags.

        Args:
            query: Search query
            tags: List of tags to filter by
            k: Number of results to return
            match_all: If True, document must have all tags; if False, any tag matches

        Returns:
            List of relevant documents filtered by tags

        Note:
            Since ChromaDB doesn't support list metadata, tags are stored as JSON strings.
            This method performs post-filtering on results.
        """
        if not tags:
            return self.similarity_search(query, k)

        # Get more results than needed for post-filtering
        results = self.similarity_search(query, k * 3)

        # Filter by tags (post-processing since tags are JSON strings)
        filtered_results = []
        for doc in results:
            doc_tags_json = doc.metadata.get("tags", "[]")
            try:
                doc_tags = json.loads(doc_tags_json) if isinstance(doc_tags_json, str) else []
            except json.JSONDecodeError:
                doc_tags = []

            # Check tag match
            if match_all:
                # All tags must be present
                if all(tag in doc_tags for tag in tags):
                    filtered_results.append(doc)
            else:
                # Any tag matches
                if any(tag in doc_tags for tag in tags):
                    filtered_results.append(doc)

            # Stop when we have enough results
            if len(filtered_results) >= k:
                break

        logger.info(f"Filtered to {len(filtered_results)} documents with tags: {tags}")
        return filtered_results[:k]

    def check_exists(self, item_id: str, doc_type: str = "article") -> bool:
        """
        Check if a document already exists in the vector store.

        Args:
            item_id: Hacker News item ID
            doc_type: Document type ("article" or "comments")

        Returns:
            True if document exists, False otherwise
        """
        try:
            # Use metadata filtering to efficiently check existence
            result = self.collection.get(
                where={"item_id": item_id, "doc_type": doc_type},
                limit=1
            )
            exists = len(result.get("ids", [])) > 0

            logger.debug(f"Document {item_id}_{doc_type} exists: {exists}")
            return exists

        except Exception as e:
            logger.error(f"Error checking existence for {item_id}_{doc_type}: {e}")
            return False

    def get_document_count(self) -> int:
        """
        Get total number of documents in the collection.

        Returns:
            Document count
        """
        try:
            count = self.collection.count()
            logger.info(f"Collection '{self.collection_name}' contains {count} documents")
            return count
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary containing collection statistics
        """
        try:
            count = self.get_document_count()

            # Get all document metadata (only metadata, no embeddings or documents)
            results = self.collection.get(
                include=["metadatas"]  # Only fetch metadata to reduce memory usage
            )

            doc_types = set()
            topics = set()
            topic_counts = {}

            for metadata in results.get("metadatas", []):
                if metadata:
                    if "doc_type" in metadata:
                        doc_types.add(metadata["doc_type"])
                    if "topic" in metadata:
                        topic = metadata["topic"]
                        topics.add(topic)
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1

            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "unique_doc_types": sorted(list(doc_types)),
                "unique_topics": sorted(list(topics)),
                "topic_counts": topic_counts,
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def delete_collection(self) -> None:
        """Delete the entire collection (use with caution)."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.warning(f"Deleted collection '{self.collection_name}'")

            # Recreate collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Recreated collection '{self.collection_name}'")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise
