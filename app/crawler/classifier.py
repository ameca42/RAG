"""
Article topic classifier module.
Uses LLM to automatically classify articles into predefined topics and generate tags.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL, TOPICS
from app.core.logger import app_logger


class TopicClassification(BaseModel):
    """Topic classification result."""
    topic: str = Field(description="Primary topic from predefined list")
    tags: List[str] = Field(description="Up to 3 relevant tags")
    confidence: str = Field(description="Confidence level: high/medium/low")


class ArticleClassifier:
    """
    Classifies articles into topics using LLM.
    """

    def __init__(self):
        # Initialize LLM with GLM-4 configuration
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=0.3,  # Lower for more consistent classification
            openai_api_base="https://open.bigmodel.cn/api/paas/v4/"  # GLM API endpoint
        )

        self.topics = TOPICS
        self.parser = PydanticOutputParser(pydantic_object=TopicClassification)

        # Create prompt template
        self.prompt = PromptTemplate(
            input_variables=["title", "content", "topics"],
            template="""You are a tech news classifier. Classify the following article into ONE primary topic and generate up to 3 relevant tags.

Available topics: {topics}

Article Title: {title}

Article Content (first 500 chars):
{content}

{format_instructions}

Return ONLY valid JSON, no additional text.""",
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

    async def classify_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a single article.

        Args:
            article: Article dict with 'title' and 'content'

        Returns:
            Article dict enhanced with 'topic', 'tags', 'classification_confidence'
        """
        title = article.get("title", "")
        content = article.get("content", "") or article.get("content_summary", "")

        if not title:
            app_logger.warning(f"Article {article.get('item_id')} has no title, skipping classification")
            return self._add_default_classification(article)

        # Truncate content to 500 chars
        content_preview = content[:500] if content else "No content available"

        try:
            # Create prompt
            prompt_text = self.prompt.format(
                title=title,
                content=content_preview,
                topics=", ".join(self.topics)
            )

            # Call LLM
            app_logger.debug(f"Classifying: {title[:50]}...")
            response = await self.llm.ainvoke(prompt_text)

            # Parse response
            result = self.parser.parse(response.content)

            # Validate topic
            if result.topic not in self.topics:
                app_logger.warning(f"LLM returned invalid topic '{result.topic}', using default")
                result.topic = "Open Source"  # Default fallback

            # Add to article
            enhanced = article.copy()
            enhanced["topic"] = result.topic
            enhanced["tags"] = result.tags[:3]  # Max 3 tags
            enhanced["classification_confidence"] = result.confidence

            app_logger.info(f"Classified '{title[:40]}...' as {result.topic}")
            return enhanced

        except json.JSONDecodeError as e:
            app_logger.error(f"JSON parse error for '{title}': {e}")
            return self._add_default_classification(article)

        except Exception as e:
            app_logger.error(f"Classification error for '{title}': {e}")
            return self._add_default_classification(article)

    def _add_default_classification(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Add default classification when LLM fails."""
        enhanced = article.copy()
        enhanced["topic"] = "Open Source"
        enhanced["tags"] = []
        enhanced["classification_confidence"] = "low"
        return enhanced

    async def classify_multiple(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify multiple articles concurrently.

        Args:
            articles: List of article dicts

        Returns:
            List of classified article dicts
        """
        app_logger.info(f"Classifying {len(articles)} articles...")

        tasks = [self.classify_article(article) for article in articles]
        results = await asyncio.gather(*tasks)

        # Count topics
        topic_counts = {}
        for article in results:
            topic = article.get("topic", "Unknown")
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        app_logger.info(f"Classification complete. Distribution: {topic_counts}")

        return results


async def classify_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to classify articles.

    Args:
        articles: List of article dicts

    Returns:
        List of classified articles
    """
    classifier = ArticleClassifier()
    return await classifier.classify_multiple(articles)


# Test function
async def test_classifier():
    """Test the classifier."""
    print("Testing Article Classifier...")
    print("-" * 50)

    # Test articles
    test_articles = [
        {
            "item_id": 1,
            "title": "Building a RAG System with LangChain and ChromaDB",
            "content": "In this tutorial, we'll explore how to build a Retrieval Augmented Generation system using LangChain and ChromaDB for vector storage..."
        },
        {
            "item_id": 2,
            "title": "PostgreSQL 16 Released with Improved Performance",
            "content": "The PostgreSQL Global Development Group announced the release of PostgreSQL 16, featuring improved query performance and new SQL commands..."
        },
        {
            "item_id": 3,
            "title": "Show HN: My Weekend Project - A Tiny Web Framework",
            "content": "I built a minimal web framework in Rust over the weekend. It's inspired by Flask but with zero-cost abstractions..."
        }
    ]

    classifier = ArticleClassifier()

    print(f"\nAvailable topics: {', '.join(TOPICS)}")
    print(f"\nClassifying {len(test_articles)} test articles...\n")

    for article in test_articles:
        print(f"Article: {article['title']}")
        classified = await classifier.classify_article(article)
        print(f"  → Topic: {classified['topic']}")
        print(f"  → Tags: {', '.join(classified['tags'])}")
        print(f"  → Confidence: {classified['classification_confidence']}")
        print()

    print("-" * 50)
    print("Classifier tests complete! ✓")


if __name__ == "__main__":
    asyncio.run(test_classifier())
