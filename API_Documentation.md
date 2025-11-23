# Hacker News RAG 系统 API 文档

## 项目概述

Hacker News RAG 系统是一个基于 AI 的智能问答和文章推荐系统，每日自动抓取 Hacker News 热门文章，提供语义搜索、智能问答、个性化推荐和评论分析等功能。

**技术栈:**
- **后端:** FastAPI + Python
- **向量数据库:** ChromaDB
- **AI 模型:** OpenAI/GPT-4 GLM-4
- **语义搜索:** LangChain + OpenAI Embeddings
- **数据源:** Hacker News API + Jina Reader

## API 基础信息

- **Base URL:** `http://localhost:8000`
- **API 版本:** `1.0.0`
- **认证方式:** 无需认证
- **数据格式:** JSON
- **字符编码:** UTF-8

## 核心数据模型

### 文章模型 (Article)

```json
{
  "item_id": 46013816,
  "title": "My private information is worth $30",
  "url": "https://blog.melashri.net/micro/privacy-price/",
  "author": "elashri",
  "score": 39,
  "descendants": 30,
  "timestamp": 1763809455,
  "crawl_date": "2025-11-22",
  "crawl_time": "2025-11-22T20:32:19.841883",
  "content_type": "article",
  "content_length": 6077,
  "content_summary": "文章内容摘要...",
  "comments_summary": "评论汇总内容...",
  "top_comments": [
    {
      "id": 123456,
      "author": "username",
      "text": "评论内容",
      "score": 15,
      "time": 1703123400
    }
  ],
  "comment_count": 10,
  "topic": "Security/Privacy",
  "tags": ["Data Breach", "Privacy", "Class Action"],
  "classification_confidence": "high"
}
```

### 用户画像模型 (User Profile)

```json
{
  "user_id": "default",
  "interests": ["AI/ML", "Security/Privacy", "Rust"],
  "reading_history": [
    {
      "item_id": "12345",
      "title": "文章标题",
      "topic": "话题分类",
      "read_at": "2025-11-22T21:40:58.963953"
    }
  ],
  "preferences": {
    "min_score": 50,
    "time_range_days": 3,
    "recommendations_count": 5
  },
  "created_at": "2025-11-22T21:40:58.961993",
  "updated_at": "2025-11-22T21:40:58.965956"
}
```

### 话题分类系统

系统支持 10 个预定义话题：
- **AI/ML** - 人工智能与机器学习
- **Programming Languages** - 编程语言
- **Web Development** - Web 开发
- **Databases** - 数据库
- **Security/Privacy** - 安全与隐私
- **Startups/Business** - 创业与商业
- **Hardware/IoT** - 硬件与物联网
- **Science** - 科学
- **Open Source** - 开源
- **Career/Jobs** - 职业与就业

---

## API 接口详情

### 1. 智能问答接口

#### 1.1 智能对话

**POST** `/api/chat`

基于向量搜索和 AI 的智能问答接口，支持自然语言查询。

**请求参数:**
```json
{
  "query": "最近有什么关于AI的好文章？",
  "user_id": "default"
}
```

**响应数据:**
```json
{
  "answer": "根据最近的文章，我为您找到了几篇优质的AI相关内容...",
  "sources": [
    {
      "item_id": 46013816,
      "title": "文章标题",
      "url": "https://example.com",
      "topic": "AI/ML",
      "score": 150,
      "snippet": "文章摘要片段..."
    }
  ],
  "filter_used": {
    "topic": "AI/ML",
    "score": {"$gte": 50}
  }
}
```

#### 1.2 文章深度分析

**POST** `/api/chat/analyze-article`

对指定文章进行深度分析，包括摘要生成和评论分析。

**请求参数:**
```
item_id (string): 文章ID
```

**响应数据:**
```json
{
  "article_info": {
    "title": "文章标题",
    "url": "https://example.com",
    "topic": "Security/Privacy",
    "score": 120,
    "tags": ["Privacy", "Data Breach"]
  },
  "summary": {
    "main_points": ["要点1", "要点2"],
    "key_insights": ["见解1", "见解2"],
    "technical_details": "技术细节",
    "impact_assessment": "影响评估"
  },
  "comments_analysis": {
    "core_controversies": "核心争议点",
    "mainstream_opinion": "主流观点",
    "valuable_insights": ["有价值见解1", "有价值见解2"],
    "sentiment": "积极/中性/消极"
  }
}
```

---

### 2. 文章浏览接口

#### 2.1 获取文章流

**GET** `/api/articles/feed`

分页获取文章列表，支持话题过滤。

**查询参数:**
- `page` (int): 页码，默认 1
- `per_page` (int): 每页数量，默认 20，最大 50
- `topic` (string, optional): 话题过滤

**响应数据:**
```json
{
  "articles": [
    {
      "item_id": 46013816,
      "title": "文章标题",
      "url": "https://example.com",
      "author": "作者",
      "score": 120,
      "descendants": 25,
      "timestamp": 1703123400,
      "crawl_date": "2025-11-22",
      "content_type": "article",
      "topic": "AI/ML",
      "tags": ["AI", "Machine Learning"],
      "ai_summary": "AI生成的文章摘要..."
    }
  ],
  "total": 1000,
  "page": 1,
  "per_page": 20
}
```

#### 2.2 获取最新文章

**GET** `/api/articles/latest`

获取最新文章列表，支持话题和分数过滤。

**查询参数:**
- `topic` (string, optional): 话题过滤
- `limit` (int): 返回数量，默认 10，最大 50
- `min_score` (int): 最低分数，默认 0

**响应数据:**
```json
{
  "articles": [...],
  "count": 15,
  "filters": {
    "topic": "AI/ML",
    "min_score": 50
  }
}
```

#### 2.3 获取文章详情

**GET** `/api/articles/{item_id}`

获取指定文章的完整详情，包括完整内容和评论。

**路径参数:**
- `item_id` (string): 文章ID

**响应数据:**
```json
{
  "article": {
    "item_id": 46013816,
    "title": "文章标题",
    "url": "https://example.com",
    "author": "作者",
    "score": 120,
    "content_summary": "完整文章内容...",
    "comments_summary": "评论汇总...",
    "top_comments": [...],
    "topic": "AI/ML",
    "tags": ["AI", "Machine Learning"]
  },
  "comments": [
    {
      "id": 123456,
      "author": "用户名",
      "text": "评论内容",
      "time": 1703123400,
      "replies": []
    }
  ]
}
```

#### 2.4 文章内对话

**POST** `/api/articles/{item_id}/chat`

基于特定文章内容进行智能对话。

**路径参数:**
- `item_id` (string): 文章ID

**请求参数:**
```json
{
  "message": "这篇文章的主要观点是什么？",
  "history": []
}
```

**响应数据:**
```json
{
  "response": "基于文章内容，主要观点是...",
  "sources": ["https://example.com/article"]
}
```

---

### 3. 文章搜索接口

#### 3.1 语义搜索

**GET** `/api/search`

基于关键词的语义搜索。

**查询参数:**
- `q` (string): 搜索关键词，必需
- `limit` (int): 返回结果数量，默认 20，最大 50

**响应数据:**
```json
{
  "results": [
    {
      "item_id": 46013816,
      "title": "相关文章标题",
      "url": "https://example.com",
      "author": "作者",
      "score": 120,
      "topic": "AI/ML",
      "tags": ["AI", "Search"],
      "ai_summary": "搜索结果摘要...",
      "snippet": "匹配的内容片段..."
    }
  ],
  "total": 25
}
```

---

### 4. 话题管理接口

#### 4.1 获取话题统计

**GET** `/api/topics`

获取所有话题及其文章数量统计。

**响应数据:**
```json
{
  "topics": [
    {
      "topic": "AI/ML",
      "count": 150
    },
    {
      "topic": "Security/Privacy",
      "count": 85
    }
  ],
  "total_topics": 10
}
```

---

### 5. 个性化推荐接口

#### 5.1 获取个性化推荐

**POST** `/api/recommend`

基于用户兴趣生成个性化文章推荐。

**请求参数:**
```json
{
  "user_id": "default",
  "days": 3,
  "top_k": 5,
  "min_score": 50
}
```

**响应数据:**
```json
{
  "recommendations": [
    {
      "item_id": 46013816,
      "title": "推荐文章标题",
      "url": "https://example.com",
      "score": 120,
      "topic": "AI/ML",
      "reason": "基于您对AI的兴趣推荐"
    }
  ],
  "explanation": "基于您对 AI/ML 和 Security/Privacy 的兴趣，为您推荐了以下文章...",
  "user_id": "default",
  "interests": ["AI/ML", "Security/Privacy"]
}
```

#### 5.2 获取相似文章

**GET** `/api/recommend/similar/{item_id}`

基于文章ID获取相似文章推荐。

**路径参数:**
- `item_id` (string): 文章ID

**查询参数:**
- `top_k` (int): 推荐数量，默认 5

**响应数据:**
```json
{
  "item_id": 46013816,
  "similar_articles": [
    {
      "item_id": 46012345,
      "title": "相似文章标题",
      "url": "https://example.com",
      "score": 110,
      "similarity_score": 0.85,
      "topic": "AI/ML"
    }
  ],
  "count": 5
}
```

---

### 6. 用户管理接口

#### 6.1 更新用户兴趣

**POST** `/api/user/interests`

更新用户的兴趣标签。

**请求参数:**
```json
{
  "user_id": "default",
  "interests": ["AI/ML", "Rust", "Databases"]
}
```

**响应数据:**
```json
{
  "message": "兴趣标签已更新",
  "user_id": "default",
  "interests": ["AI/ML", "Rust", "Databases"],
  "updated_at": "2025-11-22T21:40:58.965956"
}
```

#### 6.2 获取用户画像

**GET** `/api/user/profile/{user_id}`

获取用户完整画像信息。

**路径参数:**
- `user_id` (string): 用户ID，默认 "default"

**响应数据:**
```json
{
  "user_id": "default",
  "interests": ["AI/ML", "Security/Privacy"],
  "preferences": {
    "min_score": 50,
    "time_range_days": 3,
    "recommendations_count": 5
  },
  "reading_history": [
    {
      "item_id": "12345",
      "title": "阅读过的文章",
      "topic": "AI/ML",
      "read_at": "2025-11-22T21:40:58.963953"
    }
  ],
  "created_at": "2025-11-22T21:40:58.961993",
  "updated_at": "2025-11-22T21:40:58.965956"
}
```

#### 6.3 添加阅读历史

**POST** `/api/user/history`

将文章添加到用户阅读历史。

**请求参数:**
```
user_id (string): 用户ID
item_id (string): 文章ID
title (string): 文章标题
topic (string): 文章话题
```

**响应数据:**
```json
{
  "message": "已添加到阅读历史",
  "user_id": "default",
  "item_id": "46013816"
}
```

---

### 7. 爬虫管理接口

#### 7.1 触发爬虫任务

**POST** `/api/crawl/trigger`

手动触发 Hacker News 文章爬取任务。

**请求参数:**
```json
{
  "num_stories": 30,
  "force_refresh": false
}
```

**响应数据:**
```json
{
  "message": "爬虫任务已启动",
  "num_stories": 30,
  "status": "running"
}
```

#### 7.2 获取爬虫状态

**GET** `/api/crawl/status`

获取爬虫运行状态和统计信息。

**响应数据:**
```json
{
  "status": "completed",
  "total_crawled": 150,
  "last_crawled_ids": [46013816, 46012345, 46009876]
}
```

---

### 8. 系统接口

#### 8.1 健康检查

**GET** `/health`

检查系统健康状态。

**响应数据:**
```json
{
  "status": "healthy"
}
```

#### 8.2 根路径信息

**GET** `/`

获取API基本信息。

**响应数据:**
```json
{
  "message": "Hacker News RAG API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

#### 8.3 获取系统统计

**GET** `/api/stats`

获取向量库和系统统计信息。

**响应数据:**
```json
{
  "total_documents": 1250,
  "document_types": {
    "article": 800,
    "comments": 450
  },
  "topics": {
    "AI/ML": 150,
    "Security/Privacy": 85
  },
  "last_updated": "2025-11-22T20:32:19.841883"
}
```

---

## 错误处理

### 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "detail": "错误信息描述"
}
```

### 常见错误码

| 状态码 | 说明 | 示例场景 |
|--------|------|----------|
| 400 | 请求参数错误 | 缺少必需参数、参数格式错误 |
| 404 | 资源不存在 | 文章ID不存在、用户不存在 |
| 422 | 参数验证失败 | 参数类型错误、参数值超出范围 |
| 500 | 服务器内部错误 | 数据库连接失败、AI服务异常 |

### 典型错误示例

**文章不存在 (404):**
```json
{
  "detail": "Article not found"
}
```

**参数验证失败 (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 使用示例

### 示例 1: 智能问答流程

```bash
# 1. 设置用户兴趣
curl -X POST "http://localhost:8000/api/user/interests" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "interests": ["AI/ML", "Security/Privacy"]
  }'

# 2. 进行智能问答
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "最近有什么关于隐私保护的好文章？",
    "user_id": "user123"
  }'

# 3. 获取个性化推荐
curl -X POST "http://localhost:8000/api/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "days": 7,
    "top_k": 5
  }'
```

### 示例 2: 文章浏览和分析

```bash
# 1. 获取最新AI相关文章
curl -X GET "http://localhost:8000/api/articles/latest?topic=AI/ML&limit=10"

# 2. 获取特定文章详情
curl -X GET "http://localhost:8000/api/articles/46013816"

# 3. 分析文章内容
curl -X POST "http://localhost:8000/api/chat/analyze-article" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "46013816"
  }'
```

### 示例 3: 语义搜索

```bash
# 搜索相关文章
curl -X GET "http://localhost:8000/api/search?q=vector%20database&limit=20"

# 获取相似文章
curl -X GET "http://localhost:8000/api/recommend/similar/46013816?top_k=5"
```

---

## 性能和限制

### 请求限制
- **并发连接:** 无限制（本地部署）
- **请求频率:** 建议不超过 100 请求/分钟
- **响应超时:** 默认 30 秒

### 分页限制
- **默认页面大小:** 20
- **最大页面大小:** 50
- **搜索结果限制:** 最大 100 条

### 数据范围
- **文章保留时间:** 无限制
- **用户历史记录:** 无限制
- **话题分类:** 10 个预定义话题

---

## 部署信息

### 本地开发环境

```bash
# 启动后端服务
cd /path/to/project
./start_app.sh
# 或
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 环境变量配置

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

CHROMA_DB_PATH=./data/chromadb
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

### Docker 部署

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

---

## API 更新日志

### v1.0.0 (2025-11-22)
- ✅ 完成所有核心功能API
- ✅ 智能问答系统
- ✅ 文章浏览和搜索
- ✅ 个性化推荐
- ✅ 用户画像管理
- ✅ 爬虫管理接口
- ✅ 系统统计和监控

---

## 联系和支持

- **API 文档:** `http://localhost:8000/docs`
- **项目地址:** `/home/askeladd/Projects/RAG`
- **数据目录:** `./data/`
- **日志目录:** `./logs/`

如有问题或建议，请查看项目文档或联系开发团队。