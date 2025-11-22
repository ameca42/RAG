\*\*“Hacker News RAG 练手项目”开发进度方案\*\*。

我将整个开发周期划分为 **5 个里程碑 (Milestones)**，遵循 **"数据优先 -\> 核心逻辑 -\> 应用封装 -\> 自动化与优化"** 的路径。每个阶段都包含具体的技术任务和“完成标准”。

-----

### 🗓️ 项目总览

  * **目标：** 每日自动更新 Hacker News 知识库，支持语义检索、文章深度解读、评论区观点分析、话题分类浏览与个性化推荐。
  * **技术栈：** LangChain + ChromaDB + OpenAI Embeddings + FastAPI + Streamlit

-----

### 🚀 第一阶段：数据管道构建 (The Data Pipeline) ✅ 已完成

**目标：** 能够从 HN 获取数据，清洗干净，并在本地看到结构化的数据。

1.  **HN API 对接:** ✅
      * 使用 `httpx` (异步) 访问 Hacker News Firebase API。
      * 编写函数 `fetch_top_stories(limit=30)` 获取 Top 30 的 ID。
      * 编写函数 `fetch_item_details(id)` 获取标题、URL、分数、评论 ID 列表、时间戳。
      * **去重机制：** 记录已爬取的 `item_id`，避免重复处理（支持增量更新）。
      * **实现文件：** `app/crawler/hn_api.py`
2.  **正文爬取与清洗:** ✅
      * 集成 **Jina Reader API** (`https://r.jina.ai/{url}`)，免费无需 API Key。
      * 编写 `ArticleFetcher` 类：传入 URL，返回 Markdown 格式的正文。
      * **错误处理：**
          - 对超时、403/404 错误设置重试机制（最多 3 次，指数退避）。
          - 对 PDF、视频链接等特殊类型，标记 `content_type` 为 "non-text"，仅保留标题和元数据。
      * **实现文件：** `app/crawler/fetcher.py`
3.  **评论区递归抓取:** ✅
      * 编写递归函数处理 `kids` 字段（子评论）。
      * **策略：** 仅抓取 Top-level 评论的前 10 条及其直接子回复（每条最多 3 个），避免 Token 爆炸。
      * **数据结构化：**
          - 将评论树扁平化为字符串：`[User A]: [Content] \n  |- Reply by User B: [Content]`
          - 提取"高赞评论"（score > 20）作为单独字段 `top_comments`。
      * **实现文件：** `app/crawler/parser.py`
4.  **话题自动分类（提前实现）:** ✅
      * 使用 LLM (GLM-4) 对文章进行 10 个话题分类。
      * 自动生成 1-3 个相关标签（tags）。
      * 返回分类置信度（high/medium/low）。
      * **实现文件：** `app/crawler/classifier.py`
5.  **数据存储与去重:** ✅
      * 折中策略：存储元数据 + 2000 字符内容摘要。
      * 自动去重：通过 `crawled_ids.json` 跟踪已爬取文章。
      * **实现文件：** `app/crawler/storage.py`
6.  **异常日志与监控:** ✅
      * 使用 `loguru` 模块记录每次爬取的成功/失败数量。
      * 保存失败的 URL 到 `failed_items.json`，便于后续排查。
      * **实现文件：** `app/core/logger.py`

> **✅ 阶段完成标准：** 已达成！
> 运行 `venv/bin/python -m app.crawler.crawler -n 30` 可爬取文章并保存到 `data/articles.json`，包含：
> - `item_id`, `title`, `url`, `score`, `timestamp`, `author`
> - `content_summary` (2000字符内容摘要，或 `null` 表示 non-text)
> - `comments_summary` (格式化的评论文本)
> - `top_comments` (高赞评论列表)
> - `topic` (自动分类的话题)
> - `tags` (自动生成的标签)
> - `classification_confidence` (分类置信度)
> - `content_type`, `crawl_date`, `crawl_time`

-----

### 🧠 第二阶段：RAG 核心链路与话题分类 (The Brain) ✅ 已完成

**目标：** 将数据向量化，实现语义检索，并为每篇文章自动分类。

1.  **向量库搭建:** ✅
      * 使用 `chromadb` 和 `langchain_openai`（支持 GLM-4 API）。
      * 定义 Embedding 模型：`OpenAIEmbeddings(model="text-embedding-3-small")`。 **注意：** 如果使用 GLM-4，需要在 `.env` 中配置 `OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/`。
      * **实现文件：** `app/db/vector_store.py`
      * **核心类：** `VectorStoreManager` 提供：
          - `add_documents(docs)`: 批量添加文档到 ChromaDB（支持自动生成 ID）。
          - `similarity_search(query, k=5, filter={})`: 语义检索 + 元数据过滤（支持按 topic、doc_type、score 等过滤）。
          - `check_exists(item_id)`: 根据 HN item_id 检查文档是否已存在（支持增量更新）。
          - `get_collection_stats()`: 获取向量库统计信息。
          - `delete_collection()`: 删除整个集合（谨慎使用）。

2.  **文档切分策略:** ✅
      * **实现文件：** `app/chains/document_processor.py`
      * **核心类：** `DocumentProcessor`
      * **文章正文切分：** 使用 `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`。
      * **评论区处理：**
          - 完整评论摘要作为**单独的 Document** 存入，不切分（保留完整对话上下文）。
          - 如果评论超过 4000 字符，按段落切分（使用更大的 chunk_size=2000）。
          - 高赞评论（score ≥ 20）作为独立 document 存储，便于快速检索社区精华观点。
      * **每篇文章生成多个 Documents：**
          - 文章正文 → 1-3 个 chunks（取决于长度）。
          - 评论区 → 1 个完整摘要 + 最多 5 个高赞评论。
      * **Metadata 注入：** 每个 Document 包含：
          ```json
          {
            "item_id": "46013816",
            "source": "https://blog.melashri.net/micro/privacy-price/",
            "title": "My private information is worth $30",
            "score": 39,
            "timestamp": 1703123400,
            "author": "melashri",
            "doc_type": "article",        // or "comments"
            "chunk_index": 0,              // for multi-chunk articles
            "topic": "Security/Privacy",
            "tags": ["Data Breach", "Privacy", "Class Action"],
            "classification_confidence": "high"
          }
          ```

3.  **话题自动分类（已在第一阶段实现）:** ✅
      * **实现文件：** `app/crawler/classifier.py`
      * 使用 LLM (GLM-4) 对文章进行 10 个话题分类。
      * 自动生成 1-3 个相关标签（tags）。
      * 返回分类置信度（high/medium/low）。
      * **分类体系：**
          ```python
          TOPICS = [
              "AI/ML", "Programming Languages", "Web Development",
              "Databases", "Security/Privacy", "Startups/Business",
              "Hardware/IoT", "Science", "Open Source", "Career/Jobs"
          ]
          ```

4.  **向量存储/检索整合:** ✅
      * **实现文件：** `app/chains/vector_pipeline.py`
      * **核心类：** `VectorPipeline` 提供端到端流程：
          - `ingest_article(article)`: 单篇文章入库（自动去重）。
          - `ingest_batch(articles)`: 批量入库，返回详细统计。
          - `search(query, k=5, filter_dict)`: 通用搜索接口。
          - `search_by_topic(query, topic)`: 按话题搜索（便捷方法）。
          - `get_stats()`: 获取向量库统计。

5.  **基础检索测试:** ✅
      * **测试文件：** `test_vector_pipeline.py`
      * 测试覆盖：
          - 文档处理和向量化
          - 批量入库与去重
          - 语义搜索（通用查询）
          - 元数据过滤（按 topic、doc_type）
          - 统计信息查询
      * **示例查询：**
          ```python
          # 通用搜索
          results = pipeline.search("privacy and data protection", k=5)

          # 按话题搜索
          results = pipeline.search_by_topic("machine learning", topic="AI/ML", k=3)

          # 仅搜索评论区
          results = pipeline.search(
              "community opinions",
              k=3,
              filter_dict={"doc_type": "comments"}
          )

          # 高级过滤
          results = pipeline.search(
              "rust programming",
              k=5,
              filter_dict={
                  "topic": "Programming Languages",
                  "score": {"$gte": 50}
              }
          )
          ```

> **✅ 阶段完成标准：已达成！**
> - ✅ 向量库搭建完成，支持增量更新和元数据过滤。
> - ✅ 文档处理模块完成，自动切分文章和评论区。
> - ✅ 话题自动分类已集成（第一阶段提前实现）。
> - ✅ 基础检索功能完成，支持多种查询方式。
> - ⚠️  **注意：** 使用 GLM-4 API 时，需要确保 Embedding API 已正确配置。如果 GLM-4 不支持 embeddings，需要改用其他 embedding 服务（如 Ollama、本地模型等）。

-----

### 🕵️ 第三阶段：高级 Agent 逻辑 (The Agent) ✅ 已完成

**目标：** 实现"个性化推荐"、"深度解读"和"评论区分析"三大高级功能。

1.  **智能元数据过滤 (简化版 Self-Query):** ✅
      * **不使用** `SelfQueryRetriever`（ChromaDB 支持有限），改用自定义过滤逻辑。
      * 编写 `QueryRouter` 类：解析用户意图，生成过滤条件。
          - 示例：用户问"高分文章" → 提取关键词 → 生成 `filter={"score": {"$gte": 100}}`
          - 示例：用户问"今天的 AI 新闻" → `filter={"topic": "AI/ML", "timestamp": {"$gte": today}}`
      * 使用简单的关键词匹配 + LLM 意图识别（调用一次 LLM 生成 filter JSON）。
      * **实现文件:** `app/agents/query_router.py`
2.  **评论区深度分析 Agent:** ✅
      * 设计专门的 Prompt Template（针对评论区数据）：
          ```
          分析以下 Hacker News 评论区内容：
          {comments}

          请提供：
          1. **核心争议点**（如果存在）
          2. **社区主流观点**（正面/负面/中性）
          3. **最有价值的技术见解**（提取 1-3 条高赞评论）
          4. **情感倾向分析**（整体氛围：热烈讨论/理性分析/批评为主）
          ```
      * **不需要** Map-Reduce 链（评论已限制数量），直接调用 LLM 处理。
      * 返回结构化 JSON 结果，前端可渲染为卡片展示。
      * **实现文件:** `app/agents/comment_analysis_agent.py`
3.  **个性化推荐 Agent:** ✅
      * **用户画像存储：**
          - 使用 JSON 文件存储用户兴趣标签（如 `{"user_id": "demo", "interests": ["AI", "Rust", "Database"]}`）。
          - 每次用户点击文章或提问时，更新兴趣标签（基于文章的 topic 和 tags）。
          - 自动学习：基于阅读历史自动推断兴趣（某话题出现 3 次以上自动添加）。
          - **实现文件:** `app/db/user_profile.py`
      * **推荐逻辑：**
          - 输入：用户画像 + 时间范围（如"最近 3 天"）。
          - 检索：`filter={"tags": {"$in": user_interests}, "timestamp": {"$gte": three_days_ago}}`，按 score 降序排列。
          - LLM 生成简报：`"基于你对 AI 和 Rust 的兴趣，今天推荐以下 3 篇文章：..."`
          - **实现文件:** `app/agents/recommendation_agent.py`
4.  **文章深度解读 Agent:** ✅
      * 功能：生成文章摘要、提取关键要点、分析技术亮点、评估潜在影响。
      * 支持快速摘要生成和多文章对比。
      * **实现文件:** `app/agents/summary_agent.py`
5.  **多 Agent 协同:** ✅
      * 定义 4 个专用 Agent：
          - `QueryRouter`: 负责查询路由和过滤条件生成。
          - `RecommendationAgent`: 负责个性化推荐。
          - `SummaryAgent`: 负责文章深度解读（生成摘要 + 关键点提取）。
          - `CommentAnalysisAgent`: 负责评论区分析。
      * 使用简单的路由逻辑，根据用户提问分发给对应 Agent。

> **✅ 阶段完成标准：已达成！**
> - ✅ 系统能准确回答："帮我看看这条关于 React 的新闻，评论区里大家在吵什么？"
> - ✅ 支持个性化推荐："根据我的兴趣推荐今天的文章"（首次使用时需手动设置兴趣标签）。
> - ✅ 评论区分析返回结构化的争议点、观点和情感分析。
> - ✅ 测试文件: `test_agents.py` - 包含完整的测试套件。
> - ✅ 详细总结: 查看 `STAGE3_SUMMARY.md` 了解实现细节和使用示例。

-----

### 💻 第四阶段：应用封装与 UI (The App) ✅ 已完成

**目标：** 提供一个可视化的界面，支持话题浏览、智能对话、文章推荐。

1.  **FastAPI 后端:** ✅
      * 创建 `app/main.py`，定义核心 API 接口：
          - `POST /api/chat`: 对话接口（输入问题，返回 AI 回答 + 来源链接）。
          - `POST /api/crawl/trigger`: 手动触发爬虫（后台任务执行）。
          - `GET /api/articles/latest?topic={topic}&limit=10`: 获取最新文章列表（支持按话题过滤）。
          - `GET /api/topics`: 获取所有话题及其文章数量统计。
          - `POST /api/chat/analyze-article`: 获取指定文章的深度分析（摘要+评论）。
          - `POST /api/recommend`: 个性化推荐（输入用户兴趣，返回推荐列表）。
          - `GET /api/recommend/similar/{item_id}`: 相似文章推荐。
          - `POST /api/user/interests`: 更新用户兴趣标签。
          - `GET /api/user/profile/{user_id}`: 获取用户画像。
      * 使用异步处理，支持后台任务。
      * **实现文件:** `app/main.py`, `app/api/chat.py`, `app/api/recommend.py`, `app/api/articles.py`, `app/api/crawl.py`
2.  **Streamlit 前端:** ✅
      * **三个主要 Tab：**
          - Tab 1: "💬 智能问答" - 聊天式界面，支持上下文对话，显示参考来源
          - Tab 2: "📚 话题浏览" - 按 topic 分类展示文章，支持深度解读和相似文章推荐
          - Tab 3: "⭐ 个性化推荐" - 多选兴趣标签，一键生成个性化推荐
      * **侧边栏功能：**
          - 用户设置（用户 ID 管理）
          - 系统统计展示
          - 爬虫触发按钮
      * **智能交互：**
          - 实时聊天界面
          - 文章深度解读
          - 相似文章发现
          - 推荐理由展示
      * **实现文件:** `ui/streamlit_app.py`
3.  **一键启动脚本:** ✅
      * 创建 `start_app.sh` 脚本，同时启动 FastAPI 后端和 Streamlit 前端
      * 自动环境检查和目录创建

> **✅ 阶段完成标准：已达成！**
> - ✅ 打开浏览器 `localhost:8501`，可以：
>   - 在"智能问答"tab 与知识库对话，获取带来源的回答。
>   - 在"话题浏览"tab 按 AI/ML、Security 等话题浏览文章。
>   - 在"个性化推荐"tab 设置兴趣并获取推荐列表。
> - ✅ 点击"触发爬虫"按钮，后台自动抓取最新数据。
> - ✅ API 文档可在 http://localhost:8000/docs 查看。
> - ✅ 详细总结: 查看 `STAGE4_SUMMARY.md` 了解使用方式和 API 示例。
>
> **快速启动：**
> ```bash
> ./start_app.sh
> ```

-----

### ⚙️ 第五阶段：自动化与部署 (Automation & Deployment)

**目标：** 让系统"活"起来，实现增量更新和一键部署。

1.  **定时任务与增量更新:**
      * 引入 `APScheduler`，设置每日早上 7:00 执行 `crawl_and_ingest()` 任务。
      * **增量更新逻辑（关键优化）：**
          - 在 `VectorStoreManager` 中实现 `check_exists(item_id)` 方法。
          - 爬虫运行时，先检查 `item_id` 是否已在向量库中：
              - 如果存在 → 跳过该文章（避免重复）。
              - 如果不存在 → 执行正文爬取 + 向量化 + 入库。
          - 每次爬取前记录最新的 `max_item_id`，下次从该 ID 之后开始抓取（可选优化）。
      * **日志与监控：**
          - 使用 Python `logging` 模块，设置日志级别为 INFO。
          - 记录关键信息：爬取成功数量、失败数量、新增文章数、跳过数量。
          - 保存日志到 `logs/crawler.log`（按日期轮转）。
      * **异常处理：**
          - API 超时、网络错误时自动重试（最多 3 次）。
          - 失败的文章 ID 记录到 `data/failed_items.json`，便于人工排查。
2.  **Docker 化部署:**
      * 编写 `Dockerfile`（多阶段构建）：
          ```dockerfile
          FROM python:3.11-slim
          WORKDIR /app
          COPY requirements.txt .
          RUN pip install --no-cache-dir -r requirements.txt
          COPY . .
          CMD ["python", "app/main.py"]
          ```
      * 编写 `docker-compose.yml`（包含应用服务 + ChromaDB 持久化）：
          ```yaml
          version: '3.8'
          services:
            app:
              build: .
              ports:
                - "8000:8000"
              volumes:
                - ./data:/app/data
                - ./logs:/app/logs
              environment:
                - OPENAI_API_KEY=${OPENAI_API_KEY}
            streamlit:
              build: .
              command: streamlit run ui/streamlit_app.py
              ports:
                - "8501:8501"
          ```
      * 挂载 `data/` 目录到宿主机，确保向量库数据持久化。
3.  **环境变量管理:**
      * 创建 `.env.example` 文件（示例配置）：
          ```
          OPENAI_API_KEY=sk-...
          CHROMA_DB_PATH=./data/chromadb
          CRAWLER_SCHEDULE=0 7 * * *  # 每天 7:00
          ```
      * 使用 `python-dotenv` 加载环境变量。
4.  **文档与 README:**
      * 整理项目结构，确保代码模块化、可读性高。
      * 编写详细的 README（包含项目简介、技术栈、快速开始、API 文档）。
      * 添加 `CONTRIBUTING.md`（可选，如果开源）。

> **✅ 阶段完成标准：**
> - 执行 `docker-compose up -d` 一键启动，系统在后台运行。
> - 每日 7:00 自动爬取新文章，仅添加未入库的内容（增量更新）。
> - 日志文件记录每次爬取的详细信息（成功/失败/跳过数量）。
> - 系统重启后数据不丢失（ChromaDB 持久化）。

-----

### 📂 推荐的项目目录结构

为了让项目结构清晰，建议按以下方式组织：

```text
hn-rag/
├── app/
│   ├── api/                 # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── chat.py          # 对话接口
│   │   ├── crawl.py         # 爬虫触发接口
│   │   ├── articles.py      # 文章列表/详情接口
│   │   └── recommend.py     # 推荐接口
│   ├── core/                # 核心配置
│   │   ├── config.py        # 环境变量、常量定义
│   │   └── llm.py           # LLM 初始化（OpenAI、Prompt Templates）
│   ├── chains/              # LangChain Chain 定义
│   │   ├── qa_chain.py      # 问答链
│   │   ├── summary_chain.py # 文章摘要链
│   │   └── comment_analysis_chain.py  # 评论分析链
│   ├── crawler/             # 爬虫逻辑
│   │   ├── __init__.py
│   │   ├── hn_api.py        # HN API 对接（获取 ID、Metadata）
│   │   ├── fetcher.py       # 正文爬取（Jina Reader / AsyncHtmlLoader）
│   │   ├── parser.py        # 评论区递归解析
│   │   └── classifier.py    # 话题分类（LLM 调用）
│   ├── db/                  # 向量库操作
│   │   ├── __init__.py
│   │   ├── vector_store.py  # ChromaDB 封装（VectorStoreManager）
│   │   └── user_profile.py  # 用户画像存储（JSON/SQLite）
│   ├── agents/              # Agent 逻辑（可选，第三阶段）
│   │   ├── recommendation_agent.py
│   │   ├── comment_analysis_agent.py
│   │   └── query_router.py  # 意图识别与过滤器生成
│   ├── scheduler/           # 定时任务
│   │   └── jobs.py          # APScheduler 任务定义
│   └── main.py              # FastAPI 入口
├── ui/
│   └── streamlit_app.py     # Streamlit 前端入口
├── data/                    # 持久化数据
│   ├── chromadb/            # ChromaDB 本地存储
│   ├── user_profiles.json   # 用户兴趣标签
│   └── failed_items.json    # 爬取失败的记录
├── logs/                    # 日志文件
│   └── crawler.log
├── tests/                   # 单元测试（可选）
│   ├── test_crawler.py
│   ├── test_chains.py
│   └── test_api.py
├── .env                     # 环境变量（不提交到 Git）
├── .env.example             # 环境变量示例
├── .gitignore
├── requirements.txt         # Python 依赖
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

### 📊 核心 Metadata Schema

向量库中每个 Document 的 Metadata 应包含以下字段：

```json
{
  "item_id": 12345678,
  "source": "https://example.com/article",
  "title": "Understanding RAG Systems",
  "score": 150,
  "timestamp": 1704067200,
  "crawl_date": "2025-01-01",
  "content_type": "article",  // or "non-text", "comments"
  "doc_type": "article",       // or "comments"
  "topic": "AI/ML",
  "tags": ["RAG", "LLM", "Vector Database"]
}
```

---

### 🔧 技术栈总结

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| 数据爬取 | `httpx` (异步) + Jina Reader API | 高性能异步请求 + 智能正文提取 |
| 向量化 | `OpenAI text-embedding-3-small` | 成本低、效果好 |
| 向量库 | `ChromaDB` | 轻量级、支持元数据过滤 |
| RAG 框架 | `LangChain` | 成熟的 Chain、Agent 抽象 |
| 后端 | `FastAPI` | 高性能异步 Web 框架 |
| 前端 | `Streamlit` | 快速原型开发、支持实时交互 |
| 定时任务 | `APScheduler` | Python 原生定时调度 |
| 部署 | `Docker + docker-compose` | 容器化部署、一键启动 |

---

### 🚦 开发优先级建议

根据 MVP（最小可行产品）原则，建议优先级排序：

1. **必须实现（MVP）：**
   - 第一阶段：数据爬取与清洗
   - 第二阶段：向量库 + 基础检索 + 话题分类
   - 第三阶段：评论区分析 Agent（核心亮点）
   - 第四阶段：简易版 Streamlit（单 Tab 聊天界面）

2. **推荐实现（增强版）：**
   - 第三阶段：个性化推荐 Agent
   - 第四阶段：多 Tab UI（话题浏览 + 推荐）
   - 第五阶段：定时任务 + 增量更新

3. **可选实现（高级功能）：**
   - 第三阶段：多 Agent 协同（LangGraph）
   - 第四阶段：LangServe 接口
   - 第五阶段：Prometheus 监控

---

### 💡 进阶优化方向（完成 MVP 后）

1. **性能优化：**
   - 使用 `Redis` 缓存 LLM 响应（相同问题不重复调用）。
   - 使用 `Celery` 异步处理爬虫任务（避免阻塞 API）。

2. **功能增强：**
   - 支持"相似文章推荐"（基于向量相似度）。
   - 增加用户点赞/收藏功能，优化推荐算法（协同过滤）。
   - 支持多语言文章（自动检测语言并使用对应的 Embedding 模型）。

3. **数据分析：**
   - 统计热门话题趋势（过去 7 天各话题文章数量变化）。
   - 生成"每周精选报告"（Top 10 高分文章摘要）。

4. **部署与运维：**
   - 使用 `Nginx` 反向代理（生产环境）。
   - 配置 `GitHub Actions` CI/CD（自动测试 + 部署）。
   - 添加健康检查接口 `/health`（监控系统状态）。

---

### ✅ 改进后的方案亮点

1. **补充了话题分类功能**：在第二阶段新增 LLM 自动分类，支持按话题浏览。
2. **去除了时间估算**：专注于任务完成标准，避免不合理的时间压力。
3. **优化了技术细节**：
   - 明确增量更新逻辑（避免重复爬取）。
   - 简化 Self-Query 实现（避免过度设计）。
   - 移除 Map-Reduce 链（评论数量已限制，不需要）。
4. **增强了 UI 设计**：多 Tab 界面支持话题浏览和个性化推荐。
5. **完善了部署方案**：增加日志轮转、异常处理、数据持久化。
6. **提供了优先级指导**：明确 MVP 边界，避免过早优化。

---

### 🎯 开始实施建议

建议从第一阶段开始逐步实现，每完成一个阶段后运行测试，确保功能正常后再进入下一阶段。优先实现 MVP（前 3 个阶段 + 简易 UI），确保核心功能跑通后再做增强。祝开发顺利！
