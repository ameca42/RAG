"""
异步AI分析器 - 解决AI智能研报分析阻塞问题。
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from app.agents.summary_agent import SummaryAgent
from app.agents.comment_analysis_agent import CommentAnalysisAgent
from app.db.vector_store import VectorStoreManager
from app.core.llm import get_llm
from app.core.logger import logger


@dataclass
class AnalysisRequest:
    """分析请求对象"""
    item_id: str
    title: str
    content: str
    comments_summary: Optional[str] = None


@dataclass
class AnalysisResult:
    """分析结果对象"""
    article_info: Dict[str, Any]
    summary: Dict[str, Any]
    comments_analysis: Dict[str, Any]
    timestamp: float
    processing_time: float


class AsyncAnalyzer:
    """异步AI分析器，支持并发处理。"""

    def __init__(self):
        """初始化异步分析器。"""
        self.llm = get_llm(temperature=0.7)
        self.summary_agent = SummaryAgent()
        self.comment_agent = CommentAnalysisAgent()
        self.vector_store = VectorStoreManager()
        self.concurrency_limit = 3  # 限制并发数量
        self.executor = ThreadPoolExecutor(max_workers=4)  # 线程池

    async def analyze_article_async(self, request: AnalysisRequest) -> AnalysisResult:
        """
        异步分析单篇文章。

        Args:
            request: 分析请求对象

        Returns:
            分析结果
        """
        start_time = time.time()

        logger.info(f"Starting async analysis for article {request.item_id}")

        # 并发执行分析任务
        tasks = [
            self._analyze_summary_async(request),
            self._analyze_comments_async(request),
            self._get_article_metadata_async(request)
        ]

        # 等待所有任务完成
        summary, comments_analysis, article_info = await asyncio.gather(*tasks)

        processing_time = time.time() - start_time
        logger.info(f"Analysis completed for article {request.item_id} in {processing_time:.2f}s")

        return AnalysisResult(
            article_info=article_info,
            summary=summary,
            comments_analysis=comments_analysis,
            timestamp=time.time(),
            processing_time=processing_time
        )

    async def _analyze_summary_async(self, request: AnalysisRequest) -> Dict[str, Any]:
        """异步生成摘要。"""
        try:
            # 在线程池中执行 CPU 密集型任务
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self.summary_agent.summarize_article,
                request.title,
                request.content
            )
        except Exception as e:
            logger.error(f"Summary analysis error for {request.item_id}: {e}")
            return {"error": str(e), "summary": "分析失败"}

    async def _analyze_comments_async(self, request: AnalysisRequest) -> Dict[str, Any]:
        """异步分析评论。"""
        try:
            if not request.comments_summary:
                return {"error": "No comments provided", "analysis": "无评论数据"}

            # 在线程池中执行 CPU 密集型任务
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self.comment_agent.analyze_comments,
                request.comments_summary
            )
        except Exception as e:
            logger.error(f"Comment analysis error for {request.item_id}: {e}")
            return {"error": str(e), "analysis": "评论分析失败"}

    async def _get_article_metadata_async(self, request: AnalysisRequest) -> Dict[str, Any]:
        """异步获取文章元数据。"""
        try:
            item_id_int = int(request.item_id)
            results = self.vector_store.similarity_search(
                query="article",
                k=1,
                filter_dict={"item_id": item_id_int}
            )

            if results:
                article_results = [r for r in results if r.metadata.get("doc_type") == "article"]
                if article_results:
                    doc = article_results[0]
                    return {
                        "title": doc.metadata.get("title"),
                        "url": doc.metadata.get("source"),
                        "topic": doc.metadata.get("topic"),
                        "score": doc.metadata.get("score"),
                        "tags": doc.metadata.get("tags", "")
                    }

            return {}
        except Exception as e:
            logger.error(f"Metadata fetch error for {request.item_id}: {e}")
            return {}

    async def analyze_batch_async(self, requests: List[AnalysisRequest]) -> List[AnalysisResult]:
        """
        异步批量分析多篇文章。

        Args:
            requests: 分析请求列表

        Returns:
            分析结果列表
        """
        if not requests:
            return []

        logger.info(f"Starting batch analysis of {len(requests)} articles")

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.concurrency_limit)

        async def analyze_with_semaphore(request: AnalysisRequest) -> AnalysisResult:
            async with semaphore:
                return await self.analyze_article_async(request)

        # 并发执行所有分析
        start_time = time.time()
        results = await asyncio.gather(
            [analyze_with_semaphore(req) for req in requests],
            return_exceptions=True
        )

        # 过滤掉错误结果
        successful_results = [r for r in results if isinstance(r, AnalysisResult)]

        processing_time = time.time() - start_time
        logger.info(
            f"Batch analysis completed: {len(successful_results)}/{len(requests)} success "
            f"in {processing_time:.2f}s"
        )

        return successful_results


class AnalysisRequestQueue:
    """分析请求队列，支持缓存和批量处理。"""

    def __init__(self, max_cache_size: int = 100, batch_size: int = 5):
        self.cache: Dict[str, AnalysisResult] = {}
        self.max_cache_size = max_cache_size
        self.batch_size = batch_size
        self.pending_requests: List[AnalysisRequest] = []
        self.is_processing = False
        self.analyzer = AsyncAnalyzer()

    async def analyze_cached(self, item_id: str, title: str, content: str, comments_summary: str = None) -> AnalysisResult:
        """
        带缓存的分析请求。

        Args:
            item_id: 文章ID
            title: 文章标题
            content: 文章内容
            comments_summary: 评论摘要

        Returns:
            分析结果
        """
        # 检查缓存
        cache_key = f"{item_id}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for article {item_id}")
            return self.cache[cache_key]

        # 创建请求
        request = AnalysisRequest(
            item_id=item_id,
            title=title,
            content=content,
            comments_summary=comments_summary
        )

        # 单独分析
        result = await self.analyzer.analyze_article_async(request)

        # 缓存结果
        if len(self.cache) >= self.max_cache_size:
            # 移除最旧的缓存项
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]

        self.cache[cache_key] = result
        return result

    async def add_to_queue(self, item_id: str, title: str, content: str, comments_summary: str = None):
        """
        添加到批量处理队列。

        Args:
            item_id: 文章ID
            title: 文章标题
            content: 文章内容
            comments_summary: 评论摘要
        """
        request = AnalysisRequest(
            item_id=item_id,
            title=title,
            content=content,
            comments_summary=comments_summary
        )
        self.pending_requests.append(request)

        # 达到批量大小时触发处理
        if len(self.pending_requests) >= self.batch_size:
            await self.process_batch()

    async def process_batch(self):
        """处理批量请求队列。"""
        if not self.pending_requests or self.is_processing:
            return

        self.is_processing = True
        requests_to_process = self.pending_requests.copy()
        self.pending_requests.clear()

        try:
            results = await self.analyzer.analyze_batch_async(requests_to_process)

            # 缓存结果
            for request, result in zip(requests_to_process, results):
                cache_key = f"{request.item_id}"
                if len(self.cache) >= self.max_cache_size:
                    oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
                    del self.cache[oldest_key]
                self.cache[cache_key] = result

                logger.info(f"Cached analysis for article {request.item_id}")

        except Exception as e:
            logger.error(f"Batch analysis error: {e}")
        finally:
            self.is_processing = False

    async def flush_queue(self):
        """清空处理队列。"""
        if self.pending_requests:
            await self.process_batch()


# 全局分析器实例
analysis_queue = AnalysisRequestQueue()