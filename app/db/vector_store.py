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
from app.core.config import OPENAI_API_KEY, OPENAI_BASE_URL, CHROMA_PERSIST_DIR
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
            model="text-embedding-3-small",
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
            # Extract metadata and create IDs
            doc_ids = []
            metadatas = []

            for doc in documents:
                # Create unique ID based on item_id and doc_type
                item_id = doc.metadata.get("item_id")
                doc_type = doc.metadata.get("doc_type", "article")

                if item_id:
                    doc_id = f"{item_id}_{doc_type}"
                    doc_ids.append(doc_id)
                    metadatas.append(doc.metadata)
                else:
                    logger.warning(f"Document missing item_id in metadata: {doc.metadata}")

            # Add documents to vector store
            self.vectorstore.add_documents(
                documents=documents,
                ids=doc_ids
            )

            logger.info(f"Successfully added {len(documents)} documents to vector store")
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
            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )

            logger.info(f"Found {len(results)} relevant documents for query: {query}")

            if filter_dict:
                logger.debug(f"Applied filters: {filter_dict}")

            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

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
            expected_id = f"{item_id}_{doc_type}"
            result = self.collection.get(ids=[expected_id], limit=1)
            exists = len(result["ids"]) > 0

            logger.debug(f"Document {expected_id} exists: {exists}")
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

            # Get unique doc types
            results = self.collection.get(limit=1000)
            doc_types = set()
            topics = set()

            for metadata in results.get("metadatas", []):
                if metadata:
                    if "doc_type" in metadata:
                        doc_types.add(metadata["doc_type"])
                    if "topic" in metadata:
                        topics.add(metadata["topic"])

            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "unique_doc_types": list(doc_types),
                "unique_topics": list(topics),
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
