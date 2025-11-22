"""
LLM initialization and prompt templates.
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_EMBEDDING_MODEL


def get_llm(temperature: float = 0.7, model: str = None) -> ChatOpenAI:
    """
    Initialize and return a ChatOpenAI instance.

    Args:
        temperature: Sampling temperature (0.0 to 1.0)
        model: Model name (defaults to config value)

    Returns:
        ChatOpenAI instance
    """
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=model or OPENAI_MODEL,
        temperature=temperature
    )


def get_embeddings() -> OpenAIEmbeddings:
    """
    Initialize and return OpenAI embeddings model.

    Returns:
        OpenAIEmbeddings instance
    """
    return OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model=OPENAI_EMBEDDING_MODEL
    )


# Prompt Templates

# Topic Classification Prompt
TOPIC_CLASSIFICATION_PROMPT = PromptTemplate(
    input_variables=["title", "content", "topics"],
    template="""Based on the following article title and content, classify it into one primary topic and up to 3 relevant tags.

Available topics: {topics}

Article Title: {title}

Article Content (first 500 chars):
{content}

Return your response in JSON format:
{{
    "topic": "primary topic from the list above",
    "tags": ["tag1", "tag2", "tag3"]
}}

Only return the JSON object, no additional text.
"""
)

# Comment Analysis Prompt
COMMENT_ANALYSIS_PROMPT = PromptTemplate(
    input_variables=["comments"],
    template="""分析以下 Hacker News 评论区内容：

{comments}

请提供：
1. **核心争议点**（如果存在，如果没有则说"无明显争议"）
2. **社区主流观点**（正面/负面/中性，并简要说明）
3. **最有价值的技术见解**（提取 1-3 条高赞评论的核心观点）
4. **情感倾向分析**（整体氛围：热烈讨论/理性分析/批评为主/其他）

以 JSON 格式返回：
{{
    "controversies": ["争议点1", "争议点2"] or [],
    "mainstream_opinion": {{
        "sentiment": "positive/negative/neutral",
        "summary": "观点总结"
    }},
    "valuable_insights": ["见解1", "见解2", "见解3"],
    "overall_sentiment": "描述整体氛围"
}}

只返回 JSON 对象，不要额外文本。
"""
)

# Article Summary Prompt
ARTICLE_SUMMARY_PROMPT = PromptTemplate(
    input_variables=["title", "content"],
    template="""请对以下文章进行深度解读：

标题：{title}

正文：
{content}

请提供：
1. **核心内容摘要**（100-150字）
2. **关键要点**（3-5个要点）
3. **技术亮点**（如果有）
4. **潜在影响**（对行业/技术的影响）

以清晰的中文返回，格式如下：

## 摘要
[内容摘要]

## 关键要点
- 要点1
- 要点2
- 要点3

## 技术亮点
[技术亮点或"无特殊技术亮点"]

## 潜在影响
[影响分析]
"""
)

# Recommendation Prompt
RECOMMENDATION_PROMPT = PromptTemplate(
    input_variables=["interests", "articles"],
    template="""基于用户的兴趣标签：{interests}

以下是候选推荐文章：
{articles}

请生成个性化推荐，包括：
1. 为每篇推荐文章写一句话推荐理由（说明为什么符合用户兴趣）
2. 按相关性排序（最相关的排在前面）

返回格式（纯文本，不要 JSON）：

## 今日为你推荐

### 1. [文章标题]
推荐理由：[一句话说明]

### 2. [文章标题]
推荐理由：[一句话说明]

...
"""
)
