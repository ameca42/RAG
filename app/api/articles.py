"""
Articles API endpoints for browsing and filtering.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.db.vector_store import VectorStoreManager
from app.crawler.storage import load_articles as load_articles_from_storage
from app.agents.comment_analysis_agent import CommentAnalysisAgent
from app.agents.summary_agent import SummaryAgent
from app.core.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []


@router.get("/articles/feed")
async def get_articles_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    topic: Optional[str] = None
):
    """
    Get articles for feed display (瀑布流).

    Returns articles with AI summaries for card display.
    """
    try:
        logger.info(f"Getting feed (page={page}, per_page={per_page}, topic={topic})")

        # Load articles from storage (has full data)
        all_articles = load_articles_from_storage()

        # Filter by topic
        if topic:
            all_articles = [a for a in all_articles if a.get("topic") == topic]

        # Sort by score (descending)
        all_articles.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        articles = all_articles[start:end]

        # Format for frontend
        formatted_articles = []
        for article in articles:
            # Parse tags from JSON if needed
            tags = article.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []

            formatted_articles.append({
                "item_id": article.get("item_id"),
                "title": article.get("title"),
                "url": article.get("url"),
                "author": article.get("author"),
                "score": article.get("score", 0),
                "descendants": article.get("descendants", 0),
                "timestamp": article.get("timestamp"),
                "crawl_date": article.get("crawl_date"),
                "content_type": article.get("content_type"),
                "content_summary": article.get("content_summary"),
                "comments_summary": article.get("comments_summary"),
                "top_comments": article.get("top_comments", []),
                "topic": article.get("topic"),
                "tags": tags,
                "classification_confidence": article.get("classification_confidence"),
                "comment_count": len(article.get("top_comments", [])),  # 修复：添加comment_count字段
                "ai_summary": article.get("ai_summary") or (article.get("content_summary", "")[:150] + "..." if article.get("content_summary") else None)
            })

        return {
            "articles": formatted_articles,
            "total": len(all_articles),
            "page": page,
            "per_page": per_page
        }

    except Exception as e:
        logger.error(f"Get feed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    Get a specific article by ID with full details.
    Automatically fetches full content via Jina Reader.
    """
    try:
        logger.info(f"Getting article: {item_id}")

        item_id_int = int(item_id)

        # Load from storage for full data
        all_articles = load_articles_from_storage()
        article = next((a for a in all_articles if a.get("item_id") == item_id_int), None)

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Parse tags
        tags = article.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []

        # Always fetch full content
        full_content = None
        if article.get("url"):
            try:
                from app.crawler.fetcher import ArticleFetcher
                fetcher = ArticleFetcher()
                full_content = await fetcher.fetch_content(article.get("url"))
                if full_content:
                    logger.info(f"Fetched full content: {len(full_content)} chars")
                else:
                    logger.warning("Jina Reader returned empty content, using summary")
            except Exception as e:
                logger.warning(f"Failed to fetch full content: {e}, using summary")
                full_content = None

        # Use full content if available, otherwise fall back to summary
        content = full_content if full_content else article.get("content_summary")

        # Format comments for display
        comments = []
        top_comments = article.get("top_comments", [])
        for tc in top_comments:
            comments.append({
                "id": tc.get("id", 0),
                "author": tc.get("author", "unknown"),
                "text": tc.get("text", ""),
                "time": tc.get("time", 0),
                "replies": []
            })

        return {
            "article": {
                "item_id": article.get("item_id"),
                "title": article.get("title"),
                "url": article.get("url"),
                "author": article.get("author"),
                "score": article.get("score", 0),
                "descendants": article.get("descendants", 0),
                "timestamp": article.get("timestamp"),
                "crawl_date": article.get("crawl_date"),
                "content_type": article.get("content_type"),
                "content_summary": content,
                "comments_summary": article.get("comments_summary"),
                "top_comments": top_comments,
                "topic": article.get("topic"),
                "tags": tags,
                "classification_confidence": article.get("classification_confidence")
            },
            "comments": comments
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get article error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/{item_id}/chat")
async def chat_with_article(item_id: str, request: ChatRequest):
    """
    Chat with AI about a specific article.

    Uses the article content and comments as context.
    """
    try:
        logger.info(f"Chat about article {item_id}: {request.message[:50]}...")

        item_id_int = int(item_id)

        # Load article
        all_articles = load_articles_from_storage()
        article = next((a for a in all_articles if a.get("item_id") == item_id_int), None)

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Prepare context
        title = article.get("title", "")
        content = article.get("content_summary", "")
        comments = article.get("comments_summary", "")

        # Determine what type of question
        message_lower = request.message.lower()

        if "总结" in message_lower or "摘要" in message_lower or "summarize" in message_lower:
            # Use summary agent
            agent = SummaryAgent()
            response = agent.generate_summary(
                title=title,
                content=content,
                url=article.get("url", "")
            )
        elif "评论" in message_lower or "争议" in message_lower or "comment" in message_lower:
            # Use comment analysis agent
            if comments:
                agent = CommentAnalysisAgent()
                analysis = agent.analyze(comments)
                response = f"""**评论区分析**

**核心争议点**: {analysis.get('core_controversies', '无明显争议')}

**主流观点**: {analysis.get('mainstream_opinion', '观点多元')}

**有价值的见解**:
{chr(10).join('- ' + insight for insight in analysis.get('valuable_insights', [])[:3])}

**情感倾向**: {analysis.get('sentiment', '中性')}"""
            else:
                response = "这篇文章暂无评论数据。"
        else:
            # General question - use summary agent with custom prompt
            agent = SummaryAgent()
            context = f"""文章标题: {title}

文章内容摘要:
{content[:1500] if content else '无内容'}

评论区摘要:
{comments[:1000] if comments else '无评论'}"""

            response = agent.answer_question(
                question=request.message,
                context=context
            )

        return {
            "response": response,
            "sources": [article.get("url")] if article.get("url") else []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics():
    """
    Get all topics with article counts.
    """
    try:
        logger.info("Getting topic statistics")

        # Load articles and count by topic
        all_articles = load_articles_from_storage()

        topic_counts: Dict[str, int] = {}
        for article in all_articles:
            topic = article.get("topic", "Other")
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Sort by count (descending)
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "topics": [
                {"topic": topic, "count": count}
                for topic, count in sorted_topics
            ],
            "total_topics": len(sorted_topics)
        }

    except Exception as e:
        logger.error(f"Get topics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_articles(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Search articles by keyword.

    Uses semantic search via vector store.
    """
    try:
        logger.info(f"Searching for: {q}")

        vector_store = VectorStoreManager()

        # Semantic search
        results = vector_store.similarity_search(
            query=q,
            k=limit * 2,  # Get more for deduplication
            filter_dict={"doc_type": "article"}
        )

        # Deduplicate and format results
        seen_ids = set()
        articles = []

        for doc in results:
            item_id = doc.metadata.get("item_id")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            # Parse tags
            tags = doc.metadata.get("tags", "[]")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []

            articles.append({
                "item_id": item_id,
                "title": doc.metadata.get("title"),
                "url": doc.metadata.get("source"),
                "author": doc.metadata.get("author"),
                "score": doc.metadata.get("score", 0),
                "descendants": 0,
                "timestamp": doc.metadata.get("timestamp"),
                "crawl_date": doc.metadata.get("crawl_date", ""),
                "content_type": doc.metadata.get("content_type", ""),
                "content_summary": doc.page_content[:500] if doc.page_content else None,
                "comments_summary": None,
                "top_comments": [],
                "topic": doc.metadata.get("topic"),
                "tags": tags,
                "classification_confidence": doc.metadata.get("classification_confidence", ""),
                "ai_summary": doc.page_content[:150] + "..." if doc.page_content else None
            })

            if len(articles) >= limit:
                break

        return {
            "results": articles,
            "total": len(articles)
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
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
