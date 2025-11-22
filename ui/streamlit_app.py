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

# Page configuration
st.set_page_config(
    page_title="Hacker News 智能助手",
    page_icon="🔍",
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
    st.title("🔍 Hacker News 智能助手")

    st.divider()

    # User profile
    st.subheader("👤 用户设置")

    user_id = st.text_input("用户 ID", value=st.session_state.user_id, key="user_id_input")
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id

    # Load user profile
    if st.button("加载我的画像", use_container_width=True):
        profile = call_api(f"/user/profile/{st.session_state.user_id}")
        if profile:
            st.session_state.user_interests = profile.get("interests", [])
            st.success("画像加载成功！")

    st.divider()

    # System stats
    st.subheader("📊 系统统计")
    stats = call_api("/stats")
    if stats:
        st.metric("总文档数", stats.get("total_documents", 0))
        st.caption(f"话题数: {len(stats.get('unique_topics', []))}")

    st.divider()

    # Crawler trigger
    st.subheader("🕷️ 数据抓取")
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
tab1, tab2, tab3 = st.tabs(["💬 智能问答", "📚 话题浏览", "⭐ 个性化推荐"])


# Tab 1: Chat Interface
with tab1:
    st.header("💬 智能问答")
    st.caption("向知识库提问，获取基于 Hacker News 文章的回答")

    # Chat container
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Display sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("📎 参考来源"):
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
                        with st.expander("📎 参考来源"):
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
    st.header("📚 话题浏览")
    st.caption("按话题分类浏览 Hacker News 文章")

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

            # Display articles
            for idx, article in enumerate(articles):
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.markdown(f"### [{article['title']}]({article['url']})")
                        # tags 可能是字符串或列表
                        tags = article.get('tags', '')
                        tags_display = tags if isinstance(tags, str) else ', '.join(tags)
                        st.caption(f"话题: {article['topic']} | 标签: {tags_display}")

                    with col2:
                        st.metric("分数", article['score'])

                    # Action buttons - 使用 idx 确保 key 唯一
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(f"📝 深度解读", key=f"analyze_{article['item_id']}_{idx}"):
                            with st.spinner("分析中..."):
                                analysis = call_api(f"/chat/analyze-article?item_id={article['item_id']}", method="POST")
                                if analysis:
                                    st.json(analysis)

                    with col_b:
                        if st.button(f"🔗 相似文章", key=f"similar_{article['item_id']}_{idx}"):
                            similar_data = call_api(f"/recommend/similar/{article['item_id']}")
                            if similar_data:
                                similar = similar_data.get("similar_articles", [])
                                if similar:
                                    st.write("相似文章:")
                                    for s in similar[:3]:
                                        st.markdown(f"- [{s['title']}]({s['url']})")
                                else:
                                    st.info("未找到相似文章")

                    st.divider()


# Tab 3: Personalized Recommendations
with tab3:
    st.header("⭐ 个性化推荐")
    st.caption("基于您的兴趣标签推荐相关文章")

    # Interest management
    st.subheader("🏷️ 兴趣设置")

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

    st.divider()

    # Recommendation settings
    st.subheader("📋 推荐设置")

    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("时间范围（天）", min_value=1, max_value=30, value=7)
    with col2:
        top_k = st.slider("推荐数量", min_value=3, max_value=20, value=5)

    # Generate recommendations
    if st.button("🎯 生成推荐", use_container_width=True, type="primary"):
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
                        st.subheader("📌 为您推荐")

                        for i, rec in enumerate(recs, 1):
                            with st.container():
                                st.markdown(f"### {i}. [{rec['title']}]({rec['url']})")

                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.caption(f"📊 分数: {rec['score']}")
                                with col2:
                                    st.caption(f"🏷️ {rec['topic']}")
                                with col3:
                                    # tags 可能是字符串或列表
                                    tags = rec.get('tags', '')
                                    tags_display = tags if isinstance(tags, str) else ', '.join(tags)
                                    st.caption(f"🔖 {tags_display}")

                                st.markdown(rec.get('summary', '')[:200] + "...")

                                st.divider()
                    else:
                        st.info("暂无推荐文章，请尝试调整时间范围或更换话题")


# Footer
st.divider()
st.caption("Hacker News 智能助手 | Powered by LangChain + ChromaDB + FastAPI + Streamlit")
