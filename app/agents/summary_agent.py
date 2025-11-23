"""
Summary Agent - 文章深度解读

提供文章的深度分析，包括摘要、关键要点、技术亮点和潜在影响。
"""

from typing import Dict, Any, Optional
from langchain_core.documents import Document

from app.core.llm import get_llm, ARTICLE_SUMMARY_PROMPT
from app.core.logger import logger
from app.db.vector_store import VectorStoreManager


class SummaryAgent:
    """
    文章摘要与深度分析 Agent。

    功能：
    - 生成文章摘要
    - 提取关键要点
    - 分析技术亮点
    - 评估潜在影响
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        """
        初始化摘要 Agent。

        Args:
            vector_store: 向量存储管理器
        """
        self.llm = get_llm(temperature=0.5)
        self.vector_store = vector_store or VectorStoreManager()

    def summarize_article(self, title: str, content: str) -> Dict[str, Any]:
        """
        对文章进行深度解读。

        Args:
            title: 文章标题
            content: 文章正文

        Returns:
            结构化的分析结果
        """
        if not content or len(content.strip()) < 100:
            logger.warning("Content too short, skipping summary")
            return {
                "summary": "内容过短，无法生成摘要",
                "key_points": [],
                "technical_highlights": "N/A",
                "potential_impact": "N/A"
            }

        try:
            logger.info(f"Generating summary for article: {title}")

            # 限制内容长度（避免超过 Token 限制）
            max_content_length = 4000
            truncated_content = content[:max_content_length]

            if len(content) > max_content_length:
                truncated_content += "\n\n[内容已截断...]"

            # 生成 Prompt
            prompt_text = ARTICLE_SUMMARY_PROMPT.format(
                title=title,
                content=truncated_content
            )

            # 调用 LLM
            response = self.llm.invoke(prompt_text)
            summary_text = response.content.strip()

            # 解析结果
            parsed_result = self._parse_summary(summary_text)

            logger.info("Article summary generated successfully")
            return parsed_result

        except Exception as e:
            logger.error(f"Failed to generate article summary: {e}")
            return {
                "error": str(e),
                "summary": "摘要生成失败",
                "key_points": [],
                "technical_highlights": "N/A",
                "potential_impact": "N/A"
            }

    def summarize_by_id(self, item_id: str) -> Dict[str, Any]:
        """
        根据文章 ID 生成摘要。

        Args:
            item_id: Hacker News 文章 ID

        Returns:
            摘要结果
        """
        try:
            # 将 item_id 转为整数（ChromaDB 中存储的是 int）
            item_id_int = int(item_id)

            # 从向量库检索文章（只用单个过滤条件，避免 ChromaDB $and 问题）
            results = self.vector_store.similarity_search(
                query="article content",  # GLM-4 不支持空查询
                k=5,
                filter_dict={"item_id": item_id_int}
            )

            # 过滤出 article 类型
            article_results = [r for r in results if r.metadata.get("doc_type") == "article"]

            if not article_results:
                logger.warning(f"Article {item_id} not found")
                return {
                    "error": "文章未找到",
                    "summary": "N/A",
                    "key_points": [],
                    "technical_highlights": "N/A",
                    "potential_impact": "N/A"
                }

            # 提取文章内容（合并所有 chunks）
            article_doc = article_results[0]
            title = article_doc.metadata.get("title", "Unknown")

            # 合并所有文章 chunks
            content_parts = [doc.page_content for doc in article_results]
            content = "\n\n".join(content_parts)

            # 生成摘要
            return self.summarize_article(title, content)

        except Exception as e:
            logger.error(f"Failed to summarize article {item_id}: {e}")
            return {"error": str(e)}

    def generate_quick_summary(self, content: str, max_length: int = 150) -> str:
        """
        生成快速摘要（单段文本）。

        Args:
            content: 文章内容
            max_length: 摘要最大长度

        Returns:
            摘要文本
        """
        try:
            prompt = f"""请用一段话（不超过 {max_length} 字）总结以下内容的核心观点：

{content[:2000]}

只返回摘要文本，不要其他内容。
"""

            response = self.llm.invoke(prompt)
            summary = response.content.strip()

            # 确保不超过最大长度
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."

            return summary

        except Exception as e:
            logger.error(f"Failed to generate quick summary: {e}")
            return content[:max_length] + "..."

    def generate_summary(self, title: str, content: str, url: str = "") -> str:
        """
        生成文章摘要（用于 AI 对话）。

        Args:
            title: 文章标题
            content: 文章内容
            url: 文章 URL

        Returns:
            摘要文本
        """
        try:
            prompt = f"""请为以下文章生成一个结构化的摘要：

标题: {title}
链接: {url}

内容:
{content[:3000]}

请提供：
1. **核心观点**（2-3句话）
2. **关键要点**（3-5个要点）
3. **主要结论**

用清晰的 Markdown 格式返回。
"""

            response = self.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"摘要生成失败: {str(e)}"

    def answer_question(self, question: str, context: str) -> str:
        """
        基于上下文回答问题。

        Args:
            question: 用户问题
            context: 文章/评论上下文

        Returns:
            回答文本
        """
        try:
            prompt = f"""基于以下上下文，回答用户的问题。

上下文：
{context}

用户问题：{question}

请提供简洁、准确的回答。如果上下文中没有相关信息，请说明。
"""

            response = self.llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return f"回答生成失败: {str(e)}"

    def extract_key_points(self, content: str, num_points: int = 5) -> list[str]:
        """
        提取关键要点。

        Args:
            content: 文章内容
            num_points: 要提取的要点数量

        Returns:
            要点列表
        """
        try:
            prompt = f"""从以下内容中提取 {num_points} 个最重要的要点：

{content[:3000]}

以列表格式返回，每个要点一行，以 "- " 开头。
只返回要点列表，不要其他内容。
"""

            response = self.llm.invoke(prompt)
            points_text = response.content.strip()

            # 解析列表
            points = []
            for line in points_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    points.append(line.lstrip("-•").strip())

            return points[:num_points]

        except Exception as e:
            logger.error(f"Failed to extract key points: {e}")
            return []

    def compare_articles(self, item_ids: list[str]) -> Dict[str, Any]:
        """
        比较多篇文章的内容。

        Args:
            item_ids: 文章 ID 列表

        Returns:
            对比分析结果
        """
        if len(item_ids) < 2:
            return {"error": "至少需要 2 篇文章进行对比"}

        try:
            # 检索所有文章
            articles = []
            for item_id in item_ids:
                item_id_int = int(item_id)
                results = self.vector_store.similarity_search(
                    query="article content",
                    k=5,
                    filter_dict={"item_id": item_id_int}
                )

                # 过滤出 article 类型
                article_results = [r for r in results if r.metadata.get("doc_type") == "article"]

                if article_results:
                    doc = article_results[0]
                    # 合并所有 chunks
                    content = "\n".join([d.page_content for d in article_results])[:1000]
                    articles.append({
                        "title": doc.metadata.get("title"),
                        "content": content
                    })

            if len(articles) < 2:
                return {"error": "未找到足够的文章进行对比"}

            # 生成对比 Prompt
            articles_text = ""
            for i, article in enumerate(articles, 1):
                articles_text += f"""
### 文章 {i}: {article['title']}
{article['content']}
---
"""

            prompt = f"""请对比分析以下文章：

{articles_text}

请提供：
1. **共同主题**：这些文章的共同点
2. **差异点**：各文章的独特观点或角度
3. **互补性**：这些文章如何互补理解该主题

以清晰的结构返回分析结果。
"""

            response = self.llm.invoke(prompt)
            comparison_text = response.content.strip()

            return {
                "comparison": comparison_text,
                "articles_compared": len(articles)
            }

        except Exception as e:
            logger.error(f"Failed to compare articles: {e}")
            return {"error": str(e)}

    def _parse_summary(self, summary_text: str) -> Dict[str, Any]:
        """
        解析 LLM 生成的摘要文本。

        Args:
            summary_text: LLM 输出

        Returns:
            结构化的摘要数据
        """
        result = {
            "summary": "",
            "key_points": [],
            "technical_highlights": "",
            "potential_impact": ""
        }

        try:
            # 分割章节
            sections = summary_text.split("##")

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                # 摘要
                if section.startswith("摘要"):
                    content = section.replace("摘要", "").strip()
                    result["summary"] = content

                # 关键要点
                elif section.startswith("关键要点"):
                    content = section.replace("关键要点", "").strip()
                    # 提取列表项
                    points = []
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("-") or line.startswith("•"):
                            points.append(line.lstrip("-•").strip())
                    result["key_points"] = points

                # 技术亮点
                elif section.startswith("技术亮点"):
                    content = section.replace("技术亮点", "").strip()
                    result["technical_highlights"] = content

                # 潜在影响
                elif section.startswith("潜在影响"):
                    content = section.replace("潜在影响", "").strip()
                    result["potential_impact"] = content

            # 如果没有解析成功，返回原文
            if not result["summary"]:
                result["summary"] = summary_text[:500]

        except Exception as e:
            logger.warning(f"Failed to parse summary structure: {e}")
            result["summary"] = summary_text

        return result
