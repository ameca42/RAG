"""
Document processing and splitting for RAG pipeline.

This module handles:
- Article text splitting using RecursiveCharacterTextSplitter
- Comment documents (preserved as whole or grouped)
- Metadata injection for all documents
- Conversion from article dict to LangChain Document
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Dict, Any
from app.core.logger import logger


class DocumentProcessor:
    """Process and split articles/comments into documents for vectorization."""

    def __init__(self):
        """Initialize with text splitter configuration."""
        # For article content: chunk_size=1000, chunk_overlap=200
        self.article_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
        )

        # For comments (if needed): larger chunks to preserve context
        self.comment_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=300,
            length_function=len,
            separators=["\n---\n", "\n", ".", "?", "!"]
        )

    def process_article(self, article: Dict[str, Any]) -> List[Document]:
        """
        Process an article into one or more documents.

        Args:
            article: Article dictionary from storage

        Returns:
            List of Document objects (article chunks + comments document)
        """
        documents = []
        item_id = article.get("item_id")
        title = article.get("title", "")
        url = article.get("url", "")

        if not item_id:
            logger.error("Article missing item_id, skipping")
            return []

        # Prepare base metadata
        base_metadata = {
            "item_id": item_id,
            "source": url,
            "title": title,
            "score": article.get("score", 0),
            "timestamp": article.get("timestamp", 0),
            "crawl_date": article.get("crawl_date", ""),
            "author": article.get("author", ""),
            "content_type": article.get("content_type", "unknown"),
            "topic": article.get("topic", ""),
            "tags": article.get("tags", []),
            "classification_confidence": article.get("classification_confidence", "")
        }

        # Process article content (if available)
        content_summary = article.get("content_summary")
        if content_summary:
            # Create article documents (split into chunks)
            article_docs = self._create_article_documents(
                title=title,
                content=content_summary,
                metadata=base_metadata
            )
            documents.extend(article_docs)
            logger.info(f"Created {len(article_docs)} article chunks for '{title[:50]}...'")
        else:
            # No content available, create metadata-only document
            doc = Document(
                page_content=f"Title: {title}\nNo content available.",
                metadata={**base_metadata, "doc_type": "article"}
            )
            documents.append(doc)
            logger.info(f"Created metadata-only document for '{title[:50]}...'")

        # Process comments (if available)
        comments_summary = article.get("comments_summary")
        if comments_summary:
            comment_docs = self._create_comment_documents(
                comments_summary=comments_summary,
                base_metadata=base_metadata,
                top_comments=article.get("top_comments", [])
            )
            documents.extend(comment_docs)
            logger.info(f"Created {len(comment_docs)} comment documents")

        return documents

    def _create_article_documents(self, title: str, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """
        Create article documents by splitting content into chunks.

        Args:
            title: Article title
            content: Article content
            metadata: Base metadata

        Returns:
            List of article Document objects
        """
        # Combine title and content for better context
        full_text = f"Title: {title}\n\n{content}"

        # Split into chunks
        chunks = self.article_splitter.split_text(full_text)

        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {**metadata, "doc_type": "article", "chunk_index": i}

            # For first chunk, include title prominently
            if i == 0:
                page_content = chunk
            else:
                # For subsequent chunks, add title prefix for context
                page_content = f"Article: {title}\n\n{chunk}"

            doc = Document(page_content=page_content, metadata=chunk_metadata)
            documents.append(doc)

        return documents

    def _create_comment_documents(
        self,
        comments_summary: str,
        base_metadata: Dict[str, Any],
        top_comments: List[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Create comment documents.

        Args:
            comments_summary: Formatted comment summary string
            base_metadata: Base article metadata
            top_comments: List of high-score comments

        Returns:
            List of comment Document objects
        """
        documents = []

        # Create main comments document
        if len(comments_summary) <= 4000:
            # Single document for all comments
            comment_metadata = {**base_metadata, "doc_type": "comments", "chunk_type": "full"}
            doc = Document(
                page_content=f"Hacker News Comments:\n\n{comments_summary}",
                metadata=comment_metadata
            )
            documents.append(doc)
        else:
            # Split comments if too long (group by conversation threads)
            chunked_comments = self.comment_splitter.split_text(comments_summary)

            for i, chunk in enumerate(chunked_comments):
                comment_metadata = {
                    **base_metadata,
                    "doc_type": "comments",
                    "chunk_type": "partial",
                    "chunk_index": i
                }
                doc = Document(
                    page_content=f"Hacker News Comments (Part {i+1}):\n\n{chunk}",
                    metadata=comment_metadata
                )
                documents.append(doc)

        # Create separate documents for top comments (high-value insights)
        if top_comments:
            for i, comment in enumerate(top_comments[:5]):  # Top 5 high-score comments
                score = comment.get("score", 0)
                author = comment.get("author", "unknown")
                text = comment.get("text", "")

                if text and score >= 20:  # Only include comments with score >= 20
                    top_comment_metadata = {
                        **base_metadata,
                        "doc_type": "comments",
                        "chunk_type": "top_comment",
                        "comment_score": score,
                        "comment_author": author,
                        "comment_index": i
                    }

                    doc = Document(
                        page_content=f"High-Score Comment (Score: {score}):\nAuthor: {author}\n\n{text}",
                        metadata=top_comment_metadata
                    )
                    documents.append(doc)

        return documents

    def process_batch(self, articles: List[Dict[str, Any]]) -> List[Document]:
        """
        Process a batch of articles into documents.

        Args:
            articles: List of article dictionaries

        Returns:
            List of all Document objects
        """
        all_documents = []

        for article in articles:
            try:
                docs = self.process_article(article)
                all_documents.extend(docs)
            except Exception as e:
                title = article.get("title", "unknown")
                logger.error(f"Failed to process article '{title[:50]}...': {e}")
                continue

        logger.info(f"Processed {len(articles)} articles into {len(all_documents)} documents")
        return all_documents

    def create_search_document(
        self,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Document:
        """
        Create a single document for search/indexing purposes.

        Args:
            title: Document title
            content: Document content
            metadata: Document metadata

        Returns:
            Single Document object
        """
        page_content = f"Title: {title}\n\n{content}"
        return Document(page_content=page_content, metadata=metadata)
