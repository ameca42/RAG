\*\*“Hacker News RAG 练手项目”开发进度方案\*\*。

我将整个开发周期划分为 **5 个里程碑 (Milestones)**，遵循 **"数据优先 -\> 核心逻辑 -\> 应用封装 -\> 自动化与优化"** 的路径。每个阶段都包含具体的技术任务和“完成标准”。

-----

### 🗓️ 项目总览

  * **目标：** 每日自动更新 Hacker News 知识库，支持语义检索、文章深度解读、评论区观点分析、话题分类浏览与个性化推荐。
  * **技术栈：** LangChain + ChromaDB + OpenAI Embeddings + FastAPI + Streamlit

-----

### 🚀 第一阶段：数据管道构建 (The Data Pipeline)

**目标：** 能够从 HN 获取数据，清洗干净，并在本地看到结构化的数据。

1.  **HN API 对接:**
      * 使用 `httpx` (异步) 访问 Hacker News Firebase API。
      * 编写函数 `fetch_top_stories(limit=30)` 获取 Top 30 的 ID。
      * 编写函数 `fetch_item_details(id)` 获取标题、URL、分数、评论 ID 列表、时间戳。
      * **去重机制：** 记录已爬取的 `item_id`，避免重复处理（支持增量更新）。
2.  **正文爬取与清洗:**
      * 集成 **Jina Reader API** (`https://r.jina.ai/{url}`) 或 `LangChain AsyncHtmlLoader`。
      * 编写 `ArticleCrawler` 类：传入 URL，返回 Markdown 格式的正文。
      * **错误处理：**
          - 对超时、403/404 错误设置重试机制（最多 3 次）。
          - 对 PDF、视频链接等特殊类型，标记 `content_type` 为 "non-text"，仅保留标题和元数据。
3.  **评论区递归抓取:**
      * 编写递归函数处理 `kids` 字段（子评论）。
      * **策略：** 仅抓取 Top-level 评论的前 10 条（按分数排序）及其直接子回复（每条最多 3 个），避免 Token 爆炸。
      * **数据结构化：**
          - 将评论树扁平化为字符串：`[Score: 50] User A: [Content] \n  |- User B (reply): [Content]`
          - 提取"高赞评论"（score > 20）作为单独字段 `top_comments`。
4.  **异常日志与监控:**
      * 使用 Python `logging` 模块记录每次爬取的成功/失败数量。
      * 保存失败的 URL 到 `failed_urls.json`，便于后续排查。

> **✅ 阶段完成标准：**
> 运行脚本，本地生成一个 `data.json`，里面包含 30 条新闻，每条都有：
> - `item_id`, `title`, `url`, `score`, `timestamp`
> - `content` (Markdown 正文，或 "non-text" 标记)
> - `comments_summary` (格式化的评论文本)
> - `top_comments` (高赞评论列表)
> - `metadata` (包含 `content_type`, `crawl_date`)

-----

### 🧠 第二阶段：RAG 核心链路与话题分类 (The Brain)

**目标：** 将数据向量化，实现语义检索，并为每篇文章自动分类。

1.  **向量库搭建:**
      * 安装 `chromadb` 和 `langchain-openai`。
      * 定义 Embedding 模型：使用 `OpenAIEmbeddings(model="text-embedding-3-small")`。
      * 编写 `VectorStoreManager` 类：
          - `add_documents(docs)`: 批量添加文档到 ChromaDB。
          - `similarity_search(query, k=5, filter={})`: 语义检索 + 元数据过滤。
          - `check_exists(url)`: 根据 URL 检查文档是否已存在（增量更新支持）。
2.  **文档切分策略:**
      * 使用 `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` 切分正文。
      * **评论区处理：**
          - 评论区数据作为**单独的 Document** 存入，不切分（保留完整对话上下文）。
          - 如果评论超过 4000 字符，按"对话组"（一个主评论 + 其子回复）切分。
      * **Metadata 注入：** 每个 Chunk 必须包含：
          - `source` (URL), `title`, `score`, `item_id`, `timestamp`
          - `doc_type` ("article" 或 "comments")
          - `tags` (后续步骤生成)
          - `topic` (后续步骤生成)
3.  **话题自动分类 (新增核心功能):**
      * **定义 HN 话题分类体系：**
          ```python
          TOPICS = [
              "AI/ML", "Programming Languages", "Web Development",
              "Databases", "Security/Privacy", "Startups/Business",
              "Hardware/IoT", "Science", "Open Source", "Career/Jobs"
          ]
          ```
      * **使用 LLM 做结构化分类：**
          - 设计 Prompt：`"Based on the title and content, classify this article into one primary topic and up to 3 tags from: {TOPICS}"`
          - 使用 `langchain.output_parsers.StructuredOutputParser` 解析返回的 JSON：
            ```json
            {"topic": "AI/ML", "tags": ["ChatGPT", "LLM", "API"]}
            ```
      * **批量处理：** 对每篇文章调用 LLM 生成 topic 和 tags，更新到 Metadata。
4.  **基础检索测试:**
      * 搭建 LangChain `RetrievalQA` 链。
      * 测试用例：
          - "今天有什么关于 AI 的新闻？" → 检索 `filter={"topic": "AI/ML"}`
          - "高分 Rust 相关文章" → `filter={"score": {"$gt": 100}, "tags": {"$contains": "Rust"}}`
          - "这篇文章评论区在讨论什么？" → 检索 `filter={"doc_type": "comments", "source": url}`

> **✅ 阶段完成标准：**
> - 在 Python 终端输入问题，系统能返回基于 HN 内容的正确回答，且包含原文链接。
> - 每篇文章都有自动生成的 `topic` 和 `tags` 字段。
> - 支持按话题、标签、分数筛选检索。

-----

### 🕵️ 第三阶段：高级 Agent 逻辑 (The Agent)

**目标：** 实现"个性化推荐"、"深度解读"和"评论区分析"三大高级功能。

1.  **智能元数据过滤 (简化版 Self-Query):**
      * **不使用** `SelfQueryRetriever`（ChromaDB 支持有限），改用自定义过滤逻辑。
      * 编写 `QueryRouter` 类：解析用户意图，生成过滤条件。
          - 示例：用户问"高分文章" → 提取关键词 → 生成 `filter={"score": {"$gte": 100}}`
          - 示例：用户问"今天的 AI 新闻" → `filter={"topic": "AI/ML", "timestamp": {"$gte": today}}`
      * 使用简单的关键词匹配 + LLM 意图识别（调用一次 LLM 生成 filter JSON）。
2.  **评论区深度分析 Agent:**
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
3.  **个性化推荐 Agent:**
      * **用户画像存储：**
          - 使用 JSON 文件或 SQLite 存储用户兴趣标签（如 `{"user_id": "demo", "interests": ["AI", "Rust", "Database"]}`）。
          - 每次用户点击文章或提问时，更新兴趣标签（基于文章的 topic 和 tags）。
      * **推荐逻辑：**
          - 输入：用户画像 + 时间范围（如"最近 3 天"）。
          - 检索：`filter={"tags": {"$in": user_interests}, "timestamp": {"$gte": three_days_ago}}`，按 score 降序排列。
          - LLM 生成简报：`"基于你对 AI 和 Rust 的兴趣，今天推荐以下 3 篇文章：..."`
4.  **多 Agent 协同（可选增强）:**
      * 定义 3 个专用 Agent：
          - `RecommendationAgent`: 负责个性化推荐。
          - `SummaryAgent`: 负责文章深度解读（生成摘要 + 关键点提取）。
          - `CommentAnalysisAgent`: 负责评论区分析。
      * 使用 LangGraph 或简单的 if-else 路由，根据用户提问分发给对应 Agent。

> **✅ 阶段完成标准：**
> - 系统能准确回答："帮我看看这条关于 React 的新闻，评论区里大家在吵什么？"
> - 支持个性化推荐："根据我的兴趣推荐今天的文章"（首次使用时需手动设置兴趣标签）。
> - 评论区分析返回结构化的争议点、观点和情感分析。

-----

### 💻 第四阶段：应用封装与 UI (The App)

**目标：** 提供一个可视化的界面，支持话题浏览、智能对话、文章推荐。

1.  **FastAPI 后端:**
      * 创建 `app/main.py`，定义核心 API 接口：
          - `POST /chat`: 对话接口（输入问题，返回 AI 回答 + 来源链接）。
          - `POST /trigger-crawl`: 手动触发爬虫（返回爬取成功/失败数量）。
          - `GET /articles/latest?topic={topic}&limit=10`: 获取最新文章列表（支持按话题过滤）。
          - `GET /topics`: 获取所有话题及其文章数量统计。
          - `GET /article/{item_id}/comments`: 获取指定文章的评论区分析结果。
          - `POST /recommend`: 个性化推荐（输入用户兴趣，返回推荐列表）。
      * 使用 `asyncio` 优化 LLM 调用，避免阻塞。
2.  **Streamlit 前端:**
      * **顶部导航栏：**
          - Tab 1: "智能问答" (聊天界面)
          - Tab 2: "话题浏览" (按 topic 分类展示文章列表)
          - Tab 3: "个性化推荐" (用户设置兴趣标签，展示推荐结果)
      * **左侧侧边栏（Tab 1 专用）：**
          - 显示今日爬取的 Top Stories 列表（标题 + 分数）。
          - 点击文章标题 → 自动触发"深度解读"，在聊天窗口显示摘要 + 评论区分析。
      * **主窗口（Tab 1）：**
          - 使用 `st.chat_message` 实现流式对话。
          - 显示来源链接（可点击跳转到原文）。
      * **Tab 2 话题浏览：**
          - 左侧选择话题（如 "AI/ML"），右侧展示该话题下的文章列表。
          - 每篇文章显示：标题、分数、标签、发布时间。
          - 点击文章 → 跳转到 Tab 1 进行深度解读。
      * **Tab 3 个性化推荐：**
          - 用户勾选感兴趣的话题（Multiselect）。
          - 点击"生成推荐" → 调用 `/recommend` API，展示 Top 5 推荐文章 + AI 生成的推荐理由。
3.  **LangServe 集成（可选）:**
      * 如果需要暴露 Runnable 接口供外部调用，使用 LangServe 包装 Chain。
      * 优先级低，先确保 FastAPI + Streamlit 跑通。

> **✅ 阶段完成标准：**
> - 打开浏览器 `localhost:8501`，可以：
>   - 在"智能问答"tab 与知识库对话，获取带来源的回答。
>   - 在"话题浏览"tab 按 AI/ML、Security 等话题浏览文章。
>   - 在"个性化推荐"tab 设置兴趣并获取推荐列表。
> - 点击"触发爬虫"按钮，后台自动抓取最新数据并更新向量库。

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
