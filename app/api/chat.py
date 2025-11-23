"""
Chat API endpoints for intelligent Q&A.
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.agents.query_router import QueryRouter
from app.agents.summary_agent import SummaryAgent
from app.agents.comment_analysis_agent import CommentAnalysisAgent
from app.db.vector_store import VectorStoreManager
from app.core.llm import get_llm
from app.core.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    user_id: str = "default"


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: List[Dict[str, Any]]
    filter_used: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Intelligent chat endpoint.

    Supports:
    - Natural language queries
    - Automatic filter generation
    - Context-aware responses with sources
    """
    try:
        logger.info(f"Chat request from user {request.user_id}: {request.query}")

        # 1. Route query to extract filters
        router_agent = QueryRouter()
        routing_result = router_agent.route_query(request.query)

        filter_dict = routing_result.get("filter", {})
        k = routing_result.get("k", 5)

        logger.info(f"Applied filters: {filter_dict}")

        # 2. Search vector store
        vector_store = VectorStoreManager()
        results = vector_store.similarity_search(
            query=request.query,
            k=k,
            filter_dict=filter_dict if filter_dict else None
        )

        if not results:
            return ChatResponse(
                answer="抱歉，没有找到相关的文章。请尝试其他关键词或话题。",
                sources=[],
                filter_used=filter_dict
            )

        # 3. Generate answer using LLM
        llm = get_llm(temperature=0.7)

        # Prepare context from search results
        context = ""
        sources = []

        for i, doc in enumerate(results, 1):
            context += f"\n\n[文章 {i}]\n"
            context += f"标题: {doc.metadata.get('title', 'Unknown')}\n"
            context += f"话题: {doc.metadata.get('topic', 'Unknown')}\n"
            context += f"内容: {doc.page_content[:500]}...\n"

            sources.append({
                "item_id": doc.metadata.get("item_id"),
                "title": doc.metadata.get("title"),
                "url": doc.metadata.get("source"),
                "topic": doc.metadata.get("topic"),
                "score": doc.metadata.get("score", 0),
                "snippet": doc.page_content[:200]
            })

        # Generate answer
        prompt = f"""基于以下 Hacker News 文章内容，回答用户的问题。

用户问题: {request.query}

相关文章:
{context}

请提供一个准确、有帮助的回答。如果信息不足以回答问题，请诚实告知。
回答要简洁明了，重点突出。
"""

        response = llm.invoke(prompt)
        answer = response.content.strip()

        logger.info(f"Chat response generated with {len(sources)} sources")

        return ChatResponse(
            answer=answer,
            sources=sources,
            filter_used=filter_dict
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeArticleRequest(BaseModel):
    """Analyze article request model."""
    item_id: str


@router.post("/chat/analyze-article")
async def analyze_article(request: AnalyzeArticleRequest):
    """
    Deep analysis of a specific article (优化版 - 支持并发).

    Returns:
    - Article summary
    - Key points
    - Comment analysis
    """
    item_id = request.item_id
    try:
        logger.info(f"Starting fast analysis for article: {item_id}")

        # 从缓存获取文章基本信息
        vector_store = VectorStoreManager()
        item_id_int = int(item_id)
        results = vector_store.similarity_search(
            query="article",
            k=1,
            filter_dict={"item_id": item_id_int}
        )

        article_info = {}
        title = ""
        content = ""
        comments_summary = ""

        if results:
            article_results = [r for r in results if r.metadata.get("doc_type") == "article"]
            if article_results:
                doc = article_results[0]
                article_info = {
                    "title": doc.metadata.get("title"),
                    "url": doc.metadata.get("source"),
                    "topic": doc.metadata.get("topic"),
                    "score": doc.metadata.get("score"),
                    "tags": doc.metadata.get("tags", "")
                }
                title = doc.metadata.get("title", "")
                content = doc.page_content

        # 从存储获取评论摘要
        try:
            from app.crawler.storage import load_articles_from_storage
            all_articles = load_articles_from_storage()
            article = next((a for a in all_articles if a.get("item_id") == item_id_int), None)
            if article:
                comments_summary = article.get("comments_summary", "")
        except Exception as e:
            logger.warning(f"Failed to load article data for analysis: {e}")

        # 使用异步分析器
        from app.optimizers.async_analyzer import analysis_queue

        # 如果没有内容，不进行深度分析
        if not content and not comments_summary:
            logger.info(f"No content available for article {item_id}, skipping analysis")
            return {
                "article_info": article_info,
                "summary": {
                    "summary": "文章内容过短，无法生成深度分析",
                    "key_points": ["内容不足"],
                    "technical_highlights": "N/A",
                    "potential_impact": "N/A"
                },
                "comments_analysis": {
                    "core_controversies": "无评论数据可供分析",
                    "mainstream_opinion": "N/A",
                    "valuable_insights": [],
                    "sentiment": "中性"
                }
            }

        # 异步分析
        result = await analysis_queue.analyze_cached(
            item_id=item_id,
            title=title,
            content=content,
            comments_summary=comments_summary
        )

        logger.info(f"Fast analysis completed for article {item_id}")

        return {
            "article_info": article_info,
            "summary": result.summary,
            "comments_analysis": result.comments_analysis,
            "processing_time": result.processing_time,
            "cache_hit": result.timestamp < time.time() - 1  # 如果是1秒内，认为是缓存命中
        }

    except Exception as e:
        logger.error(f"Fast article analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
