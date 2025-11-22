"""
Articles API endpoints for browsing and filtering.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from app.db.vector_store import VectorStoreManager
from app.core.logger import logger

router = APIRouter()


@router.get("/articles/latest")
async def get_latest_articles(
    topic: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    min_score: int = Query(0, ge=0)
):
    """
    Get latest articles, optionally filtered by topic.

    Args:
        topic: Filter by topic (optional)
        limit: Number of articles to return (1-50)
        min_score: Minimum article score
    """
    try:
        logger.info(f"Getting latest articles (topic={topic}, limit={limit})")

        vector_store = VectorStoreManager()

        # 只使用单个过滤条件
        filter_dict = {"doc_type": "article"}

        # Search with a general query
        results = vector_store.similarity_search(
            query="latest news article",  # GLM-4 不支持空查询
            k=limit * 3,  # 多检索一些，后面过滤
            filter_dict=filter_dict
        )

        # 在结果中过滤 topic 和 min_score
        filtered_results = results
        if topic:
            filtered_results = [r for r in filtered_results if r.metadata.get("topic") == topic]
        if min_score > 0:
            filtered_results = [r for r in filtered_results if r.metadata.get("score", 0) >= min_score]

        # Format results（去重，按 item_id）
        seen_ids = set()
        articles = []
        for doc in filtered_results:
            item_id = doc.metadata.get("item_id")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            articles.append({
                "item_id": item_id,
                "title": doc.metadata.get("title"),
                "url": doc.metadata.get("source"),
                "score": doc.metadata.get("score", 0),
                "topic": doc.metadata.get("topic"),
                "tags": doc.metadata.get("tags", ""),
                "timestamp": doc.metadata.get("timestamp"),
                "author": doc.metadata.get("author"),
                "snippet": doc.page_content[:200] + "..."
            })

            if len(articles) >= limit:
                break

        # Sort by score (descending)
        articles.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Returned {len(articles)} articles")

        return {
            "articles": articles,
            "count": len(articles),
            "filters": {
                "topic": topic,
                "min_score": min_score
            }
        }

    except Exception as e:
        logger.error(f"Get latest articles error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/{item_id}")
async def get_article_by_id(item_id: str):
    """
    Get a specific article by ID.

    Args:
        item_id: Article ID
    """
    try:
        logger.info(f"Getting article: {item_id}")

        # 将 item_id 转为整数
        item_id_int = int(item_id)

        vector_store = VectorStoreManager()
        results = vector_store.similarity_search(
            query="article content",
            k=5,
            filter_dict={"item_id": item_id_int}
        )

        # 过滤出 article 类型
        article_results = [r for r in results if r.metadata.get("doc_type") == "article"]

        if not article_results:
            raise HTTPException(status_code=404, detail="Article not found")

        doc = article_results[0]

        # 合并所有 chunks
        content = "\n\n".join([d.page_content for d in article_results])

        article = {
            "item_id": doc.metadata.get("item_id"),
            "title": doc.metadata.get("title"),
            "url": doc.metadata.get("source"),
            "score": doc.metadata.get("score", 0),
            "topic": doc.metadata.get("topic"),
            "tags": doc.metadata.get("tags", ""),
            "timestamp": doc.metadata.get("timestamp"),
            "author": doc.metadata.get("author"),
            "content": content
        }

        return article

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get article error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics():
    """
    Get all topics with article counts.

    Returns:
    - List of topics
    - Article count per topic
    """
    try:
        logger.info("Getting topic statistics")

        vector_store = VectorStoreManager()
        stats = vector_store.get_collection_stats()

        topics = stats.get("unique_topics", [])

        # Get count for each topic（只用单个过滤条件）
        topic_counts = {}
        for topic in topics:
            results = vector_store.similarity_search(
                query="article",
                k=500,  # 限制数量
                filter_dict={"topic": topic}
            )
            # 过滤出 article 类型并去重
            seen_ids = set()
            count = 0
            for r in results:
                if r.metadata.get("doc_type") == "article":
                    item_id = r.metadata.get("item_id")
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        count += 1
            topic_counts[topic] = count

        # Sort by count (descending)
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "topics": [
                {"name": topic, "count": count}
                for topic, count in sorted_topics
            ],
            "total_topics": len(topics)
        }

    except Exception as e:
        logger.error(f"Get topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get overall collection statistics.

    Returns:
    - Total documents
    - Document types
    - Topics
    - Other metadata
    """
    try:
        logger.info("Getting collection statistics")

        vector_store = VectorStoreManager()
        stats = vector_store.get_collection_stats()

        return stats

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
