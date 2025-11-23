"""
Streamlit frontend for Hacker News RAG system.

三个主要功能 Tab:
1. 智能问答 - 与知识库对话
2. 话题浏览 - 按话题分类浏览文章
3. 个性化推荐 - 基于兴趣推荐文章
"""

import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict, Any

# Custom CSS styles
st.markdown("""
<style>
/* 全局样式 */
.stApp {
    background: #f8fafc;
}

/* 去掉不必要的边框和线条 */
.stMarkdown {
    border: none !important;
}

.stDivider {
    display: none;
}

/* 侧边栏样式 - 无滚动，紧凑 */
.css-1d391kg {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}

.css-1lcbmhc {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}

/* 侧边栏内容紧凑化 */
.sidebar-content {
    padding: 1rem 0.5rem !important;
}

/* 主标题样式 - 更紧凑 */
.main-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1e3a8a;
    text-align: center;
    margin-bottom: 1rem;
    background: linear-gradient(45deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}

/* 小卡片样式 */
.article-card {
    background: white;
    border-radius: 8px;
    padding: 0.8rem;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    border: 1px solid #e2e8f0;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
}

.article-card:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
    border-color: #3b82f6;
}

/* 卡片网格容器 */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
}

/* 卡片标题样式 */
.card-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 0.5rem 0;
    line-height: 1.3;
    color: #1e293b;
}

/* 卡片内容样式 */
.card-content {
    font-size: 0.8rem;
    color: #64748b;
    margin-bottom: 0.5rem;
    flex-grow: 1;
}

/* 卡片底部样式 */
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: #64748b;
    border-top: 1px solid #f1f5f9;
    padding-top: 0.5rem;
    margin-top: auto;
}

/* 按钮样式 - 更简洁 */
.stButton > button {
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    font-size: 0.85rem;
    padding: 0.4rem 0.8rem;
    transition: all 0.2s ease;
    box-shadow: none;
}

.stButton > button:hover {
    background: #2563eb;
    transform: none;
    box-shadow: none;
}

/* 主要按钮样式 */
.stButton > button[type="primary"] {
    background: #10b981;
}

.stButton > button[type="primary"]:hover {
    background: #059669;
}

/* 去掉指标的边框 */
.stMetric {
    background: transparent;
    padding: 0.5rem;
    border-radius: 6px;
    border: none;
    box-shadow: none;
}

/* Tab 样式 - 更简洁 */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border: none;
    box-shadow: none;
    margin-bottom: 1rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    font-weight: 600;
    padding: 0.5rem 1rem;
}

/* 输入框样式 - 去掉多余的边框 */
.stTextInput > div > div > input,
.stSelectbox > div > div > select,
.stMultiSelect > div > div > div {
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    transition: border-color 0.2s ease;
}

.stTextInput > div > div > input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

/* 滑块样式 */
.stSlider > div > div > div {
    background: #3b82f6;
}

/* 展开器样式 */
.stExpander {
    background: white;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 文章链接样式 */
.article-link {
    color: #1e40af;
    text-decoration: none;
    font-weight: 600;
    font-size: 1rem;
    line-height: 1.3;
}

.article-link:hover {
    color: #3b82f6;
    text-decoration: underline;
}

/* 容器间距 - 更紧凑 */
.content-spacing {
    padding: 0.5rem 0;
}

/* 页脚样式 */
.footer {
    text-align: center;
    margin-top: 1rem;
    padding: 0.8rem;
    color: #64748b;
    font-size: 0.85rem;
}

/* 去掉聊天消息的边框 */
.stChatMessage {
    border: none;
    border-radius: 8px;
    margin-bottom: 0.5rem;
}

/* 标题和副标题紧凑化 */
.stSubheader {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}

/* 去掉不必要的分割线 */
hr {
    display: none;
}

/* 选择器和多选框紧凑化 */
.stSelectbox, .stMultiSelect {
    margin-bottom: 0.5rem;
}

/* 按钮容器紧凑化 */
.element-container {
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Hacker News 智能助手",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_BASE_URL = "http://localhost:8000/api"

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "default"
if "user_interests" not in st.session_state:
    st.session_state.user_interests = []


def format_timestamp(timestamp: int) -> str:
    """Format Unix timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def call_api(endpoint: str, method: str = "GET", **kwargs):
    """Helper function to call API."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 调用失败: {str(e)}")
        return None


# Sidebar
with st.sidebar:
    st.markdown('<h1 class="main-title">Hacker News<br>智能助手</h1>', unsafe_allow_html=True)

    # User profile
    st.subheader("用户设置")

    user_id = st.text_input("用户 ID", value=st.session_state.user_id, key="user_id_input")
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id

    # Load user profile
    if st.button("加载我的画像", use_container_width=True):
        profile = call_api(f"/user/profile/{st.session_state.user_id}")
        if profile:
            st.session_state.user_interests = profile.get("interests", [])
            st.success("画像加载成功！")

    # System stats
    st.subheader("系统统计")
    stats = call_api("/stats")
    if stats:
        st.metric("总文档数", stats.get("total_documents", 0))
        st.caption(f"话题数: {len(stats.get('unique_topics', []))}")

    # Crawler trigger
    st.subheader("数据抓取")
    num_stories = st.number_input("抓取文章数", min_value=10, max_value=100, value=30)
    if st.button("触发爬虫", use_container_width=True):
        with st.spinner("正在启动爬虫..."):
            result = call_api(
                "/crawl/trigger",
                method="POST",
                json={"num_stories": num_stories}
            )
            if result:
                st.success(result.get("message", "任务已启动"))


# Main content tabs
tab1, tab2, tab3 = st.tabs(["智能问答", "话题浏览", "个性化推荐"])


# Tab 1: Chat Interface
with tab1:
    st.markdown('<h1 class="main-title">智能问答</h1>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; margin-bottom: 1rem; color: #64748b;">向知识库提问，获取基于 Hacker News 文章的回答</div>', unsafe_allow_html=True)

    # Chat container
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Display sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("参考来源"):
                        for i, source in enumerate(message["sources"], 1):
                            st.markdown(f"""
**{i}. [{source['title']}]({source['url']})**
- 话题: {source['topic']}
- 分数: {source['score']}
- 摘要: {source['snippet']}...
""")

    # Chat input
    if prompt := st.chat_input("请输入您的问题..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = call_api(
                    "/chat",
                    method="POST",
                    json={"query": prompt, "user_id": st.session_state.user_id}
                )

                if response:
                    answer = response.get("answer", "抱歉，无法生成回答。")
                    sources = response.get("sources", [])

                    st.markdown(answer)

                    # Display sources
                    if sources:
                        with st.expander("参考来源"):
                            for i, source in enumerate(sources, 1):
                                st.markdown(f"""
**{i}. [{source['title']}]({source['url']})**
- 话题: {source['topic']}
- 分数: {source['score']}
- 摘要: {source['snippet']}...
""")

                    # Add to message history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })


# Tab 2: Topic Browsing
with tab2:
    st.markdown('<h1 class="main-title">话题浏览</h1>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; margin-bottom: 1rem; color: #64748b;">按话题分类浏览 Hacker News 文章</div>', unsafe_allow_html=True)

    # Get topics
    topics_data = call_api("/topics")

    if topics_data:
        topics = topics_data.get("topics", [])

        # Topic selector
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_topic = st.selectbox(
                "选择话题",
                options=["全部"] + [t["name"] for t in topics],
                format_func=lambda x: f"{x} ({next((t['count'] for t in topics if t['name'] == x), 0)} 篇)" if x != "全部" else "全部"
            )

        with col2:
            min_score = st.number_input("最低分数", min_value=0, value=0, step=10)

        # Get articles
        articles_params = {"limit": 20, "min_score": min_score}
        if selected_topic != "全部":
            articles_params["topic"] = selected_topic

        articles_data = call_api("/articles/latest", params=articles_params)

        if articles_data:
            articles = articles_data.get("articles", [])

            st.caption(f"找到 {len(articles)} 篇文章")

            # Create grid of article cards
            st.markdown('<div class="cards-grid">', unsafe_allow_html=True)

            for idx, article in enumerate(articles):
                tags_text = ''
                if article.get('tags'):
                    tags = article.get('tags', '')
                    tags_text = tags if isinstance(tags, str) else ', '.join(tags)
                    if len(tags_text) > 30:  # Truncate long tags
                        tags_text = tags_text[:27] + '...'

                st.markdown(f'''
                <div class="article-card">
                    <div class="card-title">
                        <a href="{article['url']}" class="article-link" target="_blank">{article['title']}</a>
                    </div>
                    <div class="card-content">
                        <div style="margin-bottom: 0.3rem;">
                            <strong>话题:</strong> {article['topic']}
                        </div>
                        {f'<div><strong>标签:</strong> {tags_text}</div>' if tags_text else ''}
                    </div>
                    <div class="card-footer">
                        <div style="color: #3b82f6; font-weight: 600;">
                            分数: {article['score']}
                        </div>
                        <div style="display: flex; gap: 0.3rem;">
                        </div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

                # Add action buttons in separate columns below the card
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("深度解读", key=f"analyze_{article['item_id']}_{idx}", help="深度分析这篇文章"):
                        with st.spinner("分析中..."):
                            analysis = call_api(f"/chat/analyze-article?item_id={article['item_id']}", method="POST")
                            if analysis:
                                st.json(analysis)
                with col2:
                    if st.button("相似文章", key=f"similar_{article['item_id']}_{idx}", help="查找相似文章"):
                        similar_data = call_api(f"/recommend/similar/{article['item_id']}")
                        if similar_data:
                            similar = similar_data.get("similar_articles", [])
                            if similar:
                                st.write("**相似文章:**")
                                for s in similar[:3]:
                                    st.markdown(f"- [{s['title']}]({s['url']})")
                            else:
                                st.info("未找到相似文章")

            st.markdown('</div>', unsafe_allow_html=True)


# Tab 3: Personalized Recommendations
with tab3:
    st.markdown('<h1 class="main-title">个性化推荐</h1>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; margin-bottom: 1rem; color: #64748b;">基于您的兴趣标签推荐相关文章</div>', unsafe_allow_html=True)

    # Interest management
    st.subheader("兴趣设置")

    available_topics = [
        "AI/ML", "Programming Languages", "Web Development",
        "Databases", "Security/Privacy", "Startups/Business",
        "Hardware/IoT", "Science", "Open Source", "Career/Jobs"
    ]

    selected_interests = st.multiselect(
        "选择您感兴趣的话题",
        options=available_topics,
        default=st.session_state.user_interests if st.session_state.user_interests else []
    )

    if st.button("保存兴趣设置", use_container_width=True):
        result = call_api(
            "/user/interests",
            method="POST",
            json={"user_id": st.session_state.user_id, "interests": selected_interests}
        )
        if result:
            st.session_state.user_interests = selected_interests
            st.success("兴趣设置已保存！")

    # Recommendation settings
    st.subheader("推荐设置")

    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("时间范围（天）", min_value=1, max_value=30, value=7)
    with col2:
        top_k = st.slider("推荐数量", min_value=3, max_value=20, value=5)

    # Generate recommendations
    if st.button("生成推荐", use_container_width=True, type="primary"):
        if not selected_interests:
            st.warning("请先选择您的兴趣话题")
        else:
            with st.spinner("正在为您生成个性化推荐..."):
                recommendations = call_api(
                    "/recommend",
                    method="POST",
                    json={
                        "user_id": st.session_state.user_id,
                        "days": days,
                        "top_k": top_k,
                        "min_score": 0
                    }
                )

                if recommendations:
                    summary = recommendations.get("summary", "")
                    recs = recommendations.get("recommendations", [])

                    st.success(summary)

                    if recs:
                        st.subheader("为您推荐")

                        st.markdown('<div class="cards-grid">', unsafe_allow_html=True)

                        for i, rec in enumerate(recs, 1):
                            tags_text = ''
                            if rec.get('tags'):
                                tags = rec.get('tags', '')
                                tags_text = tags if isinstance(tags, str) else ', '.join(tags)
                                if len(tags_text) > 30:  # Truncate long tags
                                    tags_text = tags_text[:27] + '...'

                            summary_text = rec.get('summary', '')[:120] + '...' if rec.get('summary') else ''

                            st.markdown(f'''
                            <div class="article-card">
                                <div class="card-title">
                                    {i}. <a href="{rec['url']}" class="article-link" target="_blank">{rec['title']}</a>
                                </div>
                                <div class="card-content">
                                    <div style="margin-bottom: 0.3rem;">
                                        <strong>话题:</strong> {rec['topic']}
                                    </div>
                                    {f'<div style="margin-bottom: 0.3rem;"><strong>标签:</strong> {tags_text}</div>' if tags_text else ''}
                                    <div style="font-size: 0.75rem; color: #475569; line-height: 1.3;">
                                        {summary_text}
                                    </div>
                                </div>
                                <div class="card-footer">
                                    <div style="color: #3b82f6; font-weight: 600;">
                                        分数: {rec['score']}
                                    </div>
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)

                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("暂无推荐文章，请尝试调整时间范围或更换话题")


# Footer
st.markdown('<div class="footer">Hacker News 智能助手 | Powered by LangChain + ChromaDB + FastAPI + Streamlit</div>', unsafe_allow_html=True)
