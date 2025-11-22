"""
Recommendation Agent - 个性化推荐

基于用户兴趣标签推荐相关文章。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.llm import get_llm, RECOMMENDATION_PROMPT
from app.core.logger import logger
from app.db.vector_store import VectorStoreManager


class RecommendationAgent:
    """
    个性化推荐 Agent。

    功能：
    - 基于用户兴趣标签推荐文章
    - 时间范围过滤（如"最近 3 天"）
    - LLM 生成推荐理由
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化推荐 Agent。

        Args:
            vector_store: 向量存储管理器
        """
        self.llm = get_llm(temperature=0.7)
        self.vector_store = vector_store or VectorStoreManager()

    def recommend(
        self,
        interests: List[str],
        days: int = 3,
        top_k: int = 5,
        min_score: int = 0
    ) -> Dict[str, Any]:
        """
        基于用户兴趣推荐文章。

        Args:
            interests: 用户兴趣标签列表（如 ["AI/ML", "Rust", "Database"]）
            days: 时间范围（最近 N 天）
            top_k: 推荐文章数量
            min_score: 最低分数阈值

        Returns:
            推荐结果，包含文章列表和推荐理由
        """
        if not interests:
            logger.warning("No interests provided, returning empty recommendations")
            return {
                "recommendations": [],
                "summary": "请先设置您的兴趣标签"
            }

        try:
            logger.info(f"Generating recommendations for interests: {interests}")

            # 1. 检索相关文章
            articles = self._retrieve_articles(interests, days, top_k * 2, min_score)

            if not articles:
                return {
                    "recommendations": [],
                    "summary": f"未找到符合您兴趣的文章（最近 {days} 天）"
                }

            # 2. 使用 LLM 生成推荐理由
            recommendations = self._generate_recommendations(interests, articles, top_k)

            logger.info(f"Generated {len(recommendations)} recommendations")

            return {
                "recommendations": recommendations,
                "summary": self._format_summary(interests, len(recommendations))
            }

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return {
                "error": str(e),
                "recommendations": [],
                "summary": "推荐生成失败"
            }

    def recommend_by_query(
        self,
        query: str,
        interests: List[str],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        基于查询和用户兴趣推荐文章（混合推荐）。

        Args:
            query: 用户查询
            interests: 用户兴趣标签
            top_k: 推荐数量

        Returns:
            推荐结果
        """
        try:
            # 1. 语义检索
            semantic_results = self.vector_store.similarity_search(
                query=query,
                k=top_k * 2,
                filter_dict={"doc_type": "article"}
            )

            # 2. 基于兴趣过滤
            filtered_results = []
            for doc in semantic_results:
                topic = doc.metadata.get("topic", "")
                tags = doc.metadata.get("tags", "")
                # tags 可能是字符串
                if isinstance(tags, str):
                    tags_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
                else:
                    tags_list = [t.lower() for t in tags]

                # 检查是否匹配用户兴趣
                interests_lower = [i.lower() for i in interests]
                if topic.lower() in interests_lower or any(tag in interests_lower for tag in tags_list):
                    filtered_results.append(doc)

            # 限制数量
            filtered_results = filtered_results[:top_k]

            if not filtered_results:
                return {
                    "recommendations": [],
                    "summary": "未找到与您兴趣匹配的相关文章"
                }

            # 3. 格式化推荐结果（去重）
            seen_ids = set()
            recommendations = []
            for doc in filtered_results:
                item_id = doc.metadata.get("item_id")
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                tags = doc.metadata.get("tags", "")
                recommendations.append({
                    "item_id": item_id,
                    "title": doc.metadata.get("title"),
                    "url": doc.metadata.get("source"),
                    "score": doc.metadata.get("score", 0),
                    "topic": doc.metadata.get("topic"),
                    "tags": tags,
                    "summary": doc.page_content[:200] + "..."
                })

            return {
                "recommendations": recommendations,
                "summary": f"为您找到 {len(recommendations)} 篇相关文章"
            }

        except Exception as e:
            logger.error(f"Failed to generate query-based recommendations: {e}")
            return {"error": str(e)}

    def recommend_similar(self, item_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        推荐与指定文章相似的其他文章。

        Args:
            item_id: 文章 ID
            top_k: 推荐数量

        Returns:
            相似文章列表
        """
        try:
            # 1. 获取原文章（将 item_id 转为整数）
            item_id_int = int(item_id)
            original = self.vector_store.similarity_search(
                query="article content",
                k=5,
                filter_dict={"item_id": item_id_int}
            )

            # 过滤出 article 类型
            article_results = [r for r in original if r.metadata.get("doc_type") == "article"]

            if not article_results:
                logger.warning(f"Article {item_id} not found")
                return []

            # 2. 使用文章内容进行相似度搜索
            article_content = article_results[0].page_content
            topic = article_results[0].metadata.get("topic")

            similar_results = self.vector_store.similarity_search(
                query=article_content[:1000],  # 使用前 1000 字符
                k=top_k * 3,  # 多取一些（需要过滤和去重）
                filter_dict={"doc_type": "article"}
            )

            # 如果有 topic，在结果中过滤
            if topic:
                similar_results = [r for r in similar_results if r.metadata.get("topic") == topic]

            # 3. 移除原文章并去重
            seen_ids = set()
            similar_articles = []
            for doc in similar_results:
                doc_item_id = doc.metadata.get("item_id")
                if doc_item_id != item_id_int and doc_item_id not in seen_ids:
                    seen_ids.add(doc_item_id)
                    similar_articles.append({
                        "item_id": doc_item_id,
                        "title": doc.metadata.get("title"),
                        "url": doc.metadata.get("source"),
                        "score": doc.metadata.get("score", 0),
                        "topic": doc.metadata.get("topic"),
                        "tags": doc.metadata.get("tags", "")
                    })

            return similar_articles[:top_k]

        except Exception as e:
            logger.error(f"Failed to find similar articles for {item_id}: {e}")
            return []

    def _retrieve_articles(
        self,
        interests: List[str],
        days: int,
        limit: int,
        min_score: int
    ) -> List[Dict[str, Any]]:
        """检索符合兴趣和时间范围的文章。"""
        # 计算时间戳
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_date.timestamp())

        articles = []

        # 对每个兴趣话题进行检索（只用单个过滤条件）
        for interest in interests:
            try:
                results = self.vector_store.similarity_search(
                    query=interest,
                    k=limit,
                    filter_dict={"doc_type": "article"}
                )

                for doc in results:
                    score = doc.metadata.get("score", 0)
                    timestamp = doc.metadata.get("timestamp", 0)

                    # 在代码中过滤时间和分数
                    if score >= min_score and timestamp >= cutoff_timestamp:
                        # tags 可能是字符串
                        tags = doc.metadata.get("tags", "")
                        if isinstance(tags, str):
                            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
                        else:
                            tags_list = tags

                        articles.append({
                            "item_id": doc.metadata.get("item_id"),
                            "title": doc.metadata.get("title"),
                            "url": doc.metadata.get("source"),
                            "score": score,
                            "topic": doc.metadata.get("topic"),
                            "tags": tags_list,
                            "summary": doc.page_content[:300]
                        })

            except Exception as e:
                logger.warning(f"Failed to retrieve articles for interest '{interest}': {e}")

        # 去重并按分数排序
        unique_articles = {a["item_id"]: a for a in articles}.values()
        sorted_articles = sorted(unique_articles, key=lambda x: x["score"], reverse=True)

        return list(sorted_articles)[:limit]

    def _generate_recommendations(
        self,
        interests: List[str],
        articles: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用 LLM 生成推荐理由。"""
        try:
            # 准备文章信息
            articles_text = ""
            for i, article in enumerate(articles[:top_k], 1):
                # tags 可能是列表或字符串
                tags = article.get('tags', [])
                if isinstance(tags, list):
                    tags_str = ', '.join(tags)
                else:
                    tags_str = str(tags)

                articles_text += f"""
{i}. 【{article['topic']}】{article['title']}
   标签: {tags_str}
   分数: {article['score']}
   简介: {article['summary'][:150]}...
"""

            # 调用 LLM
            prompt_text = RECOMMENDATION_PROMPT.format(
                interests=", ".join(interests),
                articles=articles_text
            )

            response = self.llm.invoke(prompt_text)
            recommendation_text = response.content.strip()

            # 将 LLM 输出与原文章数据合并
            recommendations = []
            for article in articles[:top_k]:
                recommendations.append({
                    **article,
                    "recommendation_text": recommendation_text
                })

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate LLM recommendations: {e}")

            # 回退：返回不带 LLM 推荐理由的结果
            return articles[:top_k]

    def _format_summary(self, interests: List[str], count: int) -> str:
        """格式化推荐摘要。"""
        return f"基于您对 {', '.join(interests)} 的兴趣，为您推荐了 {count} 篇文章。"
