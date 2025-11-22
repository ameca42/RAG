"""
Query Router - 智能元数据过滤器

解析用户查询意图，生成适当的过滤条件。
不使用 SelfQueryRetriever（ChromaDB 支持有限），改用自定义过滤逻辑。
"""

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.llm import get_llm
from app.core.logger import logger


class QueryRouter:
    """
    智能查询路由器，解析用户意图并生成元数据过滤条件。

    功能：
    - 关键词匹配（高分文章、今天的新闻等）
    - LLM 意图识别（生成过滤 JSON）
    - 支持复杂过滤（topic、score、timestamp 等）
    """

    # 话题列表
    TOPICS = [
        "AI/ML", "Programming Languages", "Web Development",
        "Databases", "Security/Privacy", "Startups/Business",
        "Hardware/IoT", "Science", "Open Source", "Career/Jobs"
    ]

    # 关键词到话题的映射
    TOPIC_KEYWORDS = {
        "ai": "AI/ML",
        "ml": "AI/ML",
        "machine learning": "AI/ML",
        "artificial intelligence": "AI/ML",
        "deep learning": "AI/ML",
        "rust": "Programming Languages",
        "python": "Programming Languages",
        "javascript": "Programming Languages",
        "react": "Web Development",
        "vue": "Web Development",
        "web": "Web Development",
        "database": "Databases",
        "sql": "Databases",
        "postgres": "Databases",
        "security": "Security/Privacy",
        "privacy": "Security/Privacy",
        "startup": "Startups/Business",
        "business": "Startups/Business",
        "hardware": "Hardware/IoT",
        "iot": "Hardware/IoT",
        "science": "Science",
        "open source": "Open Source",
        "career": "Career/Jobs",
        "jobs": "Career/Jobs",
    }

    def __init__(self):
        """初始化查询路由器。"""
        self.llm = get_llm(temperature=0.0)

    def route_query(self, query: str) -> Dict[str, Any]:
        """
        解析查询并生成过滤条件。

        Args:
            query: 用户查询字符串

        Returns:
            包含过滤条件的字典，格式：
            {
                "filter": {...},  # ChromaDB 过滤条件
                "needs_llm": bool,  # 是否需要 LLM 处理
                "k": int  # 返回结果数量
            }
        """
        logger.info(f"Routing query: {query}")

        # 先尝试简单关键词匹配
        simple_filter = self._extract_simple_filters(query)
        if simple_filter:
            logger.info(f"Applied simple filters: {simple_filter}")
            return {
                "filter": simple_filter,
                "needs_llm": False,
                "k": self._extract_result_count(query)
            }

        # 如果简单匹配失败，使用 LLM 意图识别
        llm_filter = self._llm_intent_extraction(query)
        return {
            "filter": llm_filter,
            "needs_llm": True,
            "k": self._extract_result_count(query)
        }

    def _extract_simple_filters(self, query: str) -> Optional[Dict[str, Any]]:
        """
        使用关键词匹配提取简单过滤条件。

        Args:
            query: 用户查询

        Returns:
            过滤条件字典，如果无法匹配则返回 None
        """
        filter_dict = {}
        query_lower = query.lower()

        # 1. 提取话题
        for keyword, topic in self.TOPIC_KEYWORDS.items():
            if keyword in query_lower:
                filter_dict["topic"] = topic
                break

        # 2. 提取分数过滤
        # 匹配 "高分"、"hot"、"popular"、"score > 100" 等
        if any(kw in query_lower for kw in ["高分", "hot", "popular", "热门"]):
            filter_dict["score"] = {"$gte": 100}

        # 匹配具体分数，如 "score > 50"
        score_match = re.search(r'score\s*>\s*(\d+)', query_lower)
        if score_match:
            threshold = int(score_match.group(1))
            filter_dict["score"] = {"$gte": threshold}

        # 3. 提取时间过滤
        # 匹配 "今天"、"today"、"最近"、"recent"
        now = datetime.now()
        if any(kw in query_lower for kw in ["今天", "today"]):
            today_start = datetime(now.year, now.month, now.day)
            filter_dict["timestamp"] = {"$gte": int(today_start.timestamp())}

        elif any(kw in query_lower for kw in ["最近", "recent", "latest", "最新"]):
            # 最近 3 天
            three_days_ago = now - timedelta(days=3)
            filter_dict["timestamp"] = {"$gte": int(three_days_ago.timestamp())}

        # 匹配具体天数，如 "最近 7 天"
        days_match = re.search(r'最近\s*(\d+)\s*天', query)
        if not days_match:
            days_match = re.search(r'last\s+(\d+)\s+days?', query_lower)

        if days_match:
            days = int(days_match.group(1))
            past_date = now - timedelta(days=days)
            filter_dict["timestamp"] = {"$gte": int(past_date.timestamp())}

        # 4. 提取文档类型
        if any(kw in query_lower for kw in ["评论", "comments", "discussion"]):
            filter_dict["doc_type"] = "comments"
        elif any(kw in query_lower for kw in ["文章", "article", "正文"]):
            filter_dict["doc_type"] = "article"

        # 如果没有提取到任何过滤条件，返回 None
        if not filter_dict:
            return None

        return filter_dict

    def _llm_intent_extraction(self, query: str) -> Dict[str, Any]:
        """
        使用 LLM 提取查询意图并生成过滤条件。

        Args:
            query: 用户查询

        Returns:
            过滤条件字典
        """
        prompt = f"""分析以下用户查询，提取过滤条件。

可用话题列表：{', '.join(self.TOPICS)}

用户查询：{query}

请提取以下过滤条件（如果适用）：
1. topic（话题，必须是上述列表中的一个）
2. score（分数，使用 {{"$gte": 数字}} 格式）
3. timestamp（时间戳，Unix 时间戳，使用 {{"$gte": 数字}} 格式）
4. doc_type（文档类型："article" 或 "comments"）

以 JSON 格式返回过滤条件，只返回 JSON，不要其他文本：
{{
    "topic": "话题名称或null",
    "score": {{"$gte": 数字}} 或 null,
    "timestamp": {{"$gte": 数字}} 或 null,
    "doc_type": "article/comments" 或 null
}}

如果某个条件不适用，设置为 null。
"""

        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()

            # 提取 JSON（移除可能的 markdown 代码块标记）
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            # 解析 JSON
            filter_data = json.loads(result_text)

            # 移除 null 值
            filter_dict = {k: v for k, v in filter_data.items() if v is not None}

            logger.info(f"LLM extracted filters: {filter_dict}")
            return filter_dict

        except Exception as e:
            logger.error(f"LLM intent extraction failed: {e}")
            # 返回空过滤条件
            return {}

    def _extract_result_count(self, query: str) -> int:
        """
        从查询中提取期望的结果数量。

        Args:
            query: 用户查询

        Returns:
            结果数量（默认 5）
        """
        # 匹配 "top 10"、"前 5 篇"、"5 个" 等
        patterns = [
            r'top\s+(\d+)',
            r'前\s*(\d+)',
            r'(\d+)\s*个',
            r'(\d+)\s*篇',
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                count = int(match.group(1))
                return min(count, 20)  # 限制最多 20 个结果

        return 5  # 默认返回 5 个结果
