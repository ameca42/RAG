"""
Comment Analysis Agent - 评论区深度分析

专门处理 Hacker News 评论区数据，提供结构化的分析结果。
"""

import json
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document

from app.core.llm import get_llm, COMMENT_ANALYSIS_PROMPT
from app.core.logger import logger
from app.db.vector_store import VectorStoreManager


class CommentAnalysisAgent:
    """
    评论区分析 Agent。

    功能：
    - 提取核心争议点
    - 分析社区主流观点
    - 提取有价值的技术见解
    - 情感倾向分析
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化评论分析 Agent。

        Args:
            vector_store: 向量存储管理器（可选，用于检索评论）
        """
        self.llm = get_llm(temperature=0.3)
        self.vector_store = vector_store or VectorStoreManager()

    def analyze_comments(self, comments: str, article_title: Optional[str] = None) -> Dict[str, Any]:
        """
        分析评论内容。

        Args:
            comments: 评论文本（格式化的评论摘要）
            article_title: 文章标题（可选，用于更好的上下文理解）

        Returns:
            结构化的分析结果
        """
        if not comments or len(comments.strip()) < 50:
            logger.warning("Comments too short or empty, skipping analysis")
            return {
                "controversies": [],
                "mainstream_opinion": {
                    "sentiment": "neutral",
                    "summary": "评论数量不足，无法分析"
                },
                "valuable_insights": [],
                "overall_sentiment": "无足够数据"
            }

        try:
            logger.info(f"Analyzing comments for article: {article_title or 'Unknown'}")

            # 准备 Prompt
            prompt_text = COMMENT_ANALYSIS_PROMPT.format(comments=comments[:4000])  # 限制长度

            # 调用 LLM
            response = self.llm.invoke(prompt_text)
            result_text = response.content.strip()

            # 解析 JSON 响应
            analysis_result = self._parse_json_response(result_text)

            logger.info("Comment analysis completed successfully")
            return analysis_result

        except Exception as e:
            logger.error(f"Failed to analyze comments: {e}")
            return {
                "error": str(e),
                "controversies": [],
                "mainstream_opinion": {"sentiment": "neutral", "summary": "分析失败"},
                "valuable_insights": [],
                "overall_sentiment": "分析出错"
            }

    def analyze_article_comments(self, item_id: str) -> Dict[str, Any]:
        """
        根据文章 ID 检索并分析评论。

        Args:
            item_id: Hacker News 文章 ID

        Returns:
            分析结果
        """
        try:
            # 将 item_id 转为整数（ChromaDB 中存储的是 int）
            item_id_int = int(item_id)

            # 从向量库中检索评论（只用单个过滤条件）
            results = self.vector_store.similarity_search(
                query="comments discussion",  # GLM-4 不支持空查询
                k=10,
                filter_dict={"item_id": item_id_int}
            )

            # 过滤出 comments 类型
            comment_results = [r for r in results if r.metadata.get("doc_type") == "comments"]

            if not comment_results:
                logger.warning(f"No comments found for item_id: {item_id}")
                return {
                    "error": "未找到评论数据",
                    "controversies": [],
                    "mainstream_opinion": {"sentiment": "neutral", "summary": "无评论"},
                    "valuable_insights": [],
                    "overall_sentiment": "无评论"
                }

            # 合并所有评论内容
            comments_text = "\n\n".join([doc.page_content for doc in comment_results])
            article_title = comment_results[0].metadata.get("title", "Unknown")

            # 分析评论
            return self.analyze_comments(comments_text, article_title)

        except Exception as e:
            logger.error(f"Failed to analyze article comments for {item_id}: {e}")
            return {"error": str(e)}

    def get_top_comments(self, item_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        获取文章的高赞评论。

        Args:
            item_id: Hacker News 文章 ID
            top_k: 返回的高赞评论数量

        Returns:
            高赞评论列表
        """
        try:
            # 将 item_id 转为整数
            item_id_int = int(item_id)

            # 检索评论
            results = self.vector_store.similarity_search(
                query="top comment discussion",
                k=top_k * 2,  # 多检索一些，后面过滤
                filter_dict={"item_id": item_id_int}
            )

            # 过滤出评论类型
            comment_results = [r for r in results if r.metadata.get("doc_type") in ["comments", "top_comment"]]

            top_comments = []
            for doc in comment_results[:top_k]:
                top_comments.append({
                    "content": doc.page_content,
                    "author": doc.metadata.get("author", "Unknown"),
                    "score": doc.metadata.get("score", 0)
                })

            logger.info(f"Retrieved {len(top_comments)} top comments for {item_id}")
            return top_comments

        except Exception as e:
            logger.error(f"Failed to get top comments for {item_id}: {e}")
            return []

    def compare_opinions(self, query: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        比较多篇文章的评论区观点。

        Args:
            query: 查询关键词
            topic: 话题过滤（可选）

        Returns:
            观点对比结果
        """
        try:
            # 构建过滤条件（单条件，避免 ChromaDB $and 问题）
            filter_dict = {"doc_type": "comments"}

            # 检索相关评论
            results = self.vector_store.similarity_search(
                query=query,
                k=10,
                filter_dict=filter_dict
            )

            # 如果指定了 topic，在结果中过滤
            if topic:
                results = [r for r in results if r.metadata.get("topic") == topic]

            if not results:
                return {"error": "未找到相关评论"}

            # 汇总所有评论
            all_comments = "\n\n---分隔线---\n\n".join([doc.page_content for doc in results])

            # 生成对比分析 Prompt
            comparison_prompt = f"""以下是关于"{query}"的多篇文章的评论区内容：

{all_comments[:5000]}

请对比分析这些评论区的观点：
1. **共同点**：大家普遍认同的观点
2. **分歧点**：存在争议的话题
3. **有趣发现**：特别有价值或有趣的观点

以 JSON 格式返回：
{{
    "common_views": ["观点1", "观点2"],
    "disagreements": ["争议1", "争议2"],
    "interesting_findings": ["发现1", "发现2"]
}}
"""

            response = self.llm.invoke(comparison_prompt)
            result = self._parse_json_response(response.content.strip())

            logger.info(f"Opinion comparison completed for query: {query}")
            return result

        except Exception as e:
            logger.error(f"Failed to compare opinions: {e}")
            return {"error": str(e)}

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的 JSON 响应。

        Args:
            response_text: LLM 响应文本

        Returns:
            解析后的字典
        """
        try:
            # 移除可能的 markdown 代码块标记
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # 解析 JSON
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text}")

            # 返回默认结构
            return {
                "controversies": [],
                "mainstream_opinion": {"sentiment": "neutral", "summary": "解析失败"},
                "valuable_insights": [],
                "overall_sentiment": "数据格式错误"
            }
