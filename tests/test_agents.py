"""
测试第三阶段的所有 Agent 功能。

运行方式：
    venv/bin/python test_agents.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.query_router import QueryRouter
from app.agents.comment_analysis_agent import CommentAnalysisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.summary_agent import SummaryAgent
from app.db.user_profile import UserProfileManager
from app.db.vector_store import VectorStoreManager
from app.core.logger import logger


def test_query_router():
    """测试查询路由器。"""
    print("\n" + "=" * 60)
    print("测试 1: QueryRouter - 智能元数据过滤")
    print("=" * 60)

    router = QueryRouter()

    # 测试用例
    test_queries = [
        "今天的 AI 新闻",
        "高分 Rust 文章",
        "最近 7 天的数据库相关内容",
        "前 10 篇关于 security 的文章",
        "评论区关于 React 的讨论"
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        result = router.route_query(query)
        print(f"过滤条件: {result['filter']}")
        print(f"结果数量: {result['k']}")
        print(f"需要 LLM: {result['needs_llm']}")


def test_user_profile():
    """测试用户画像管理。"""
    print("\n" + "=" * 60)
    print("测试 2: UserProfileManager - 用户画像管理")
    print("=" * 60)

    manager = UserProfileManager()

    # 1. 创建/获取用户画像
    print("\n1. 获取默认用户画像:")
    profile = manager.get_profile("test_user")
    print(f"兴趣: {profile['interests']}")
    print(f"偏好设置: {profile['preferences']}")

    # 2. 更新兴趣
    print("\n2. 更新用户兴趣:")
    manager.update_interests(["AI/ML", "Rust", "Databases"], "test_user")
    updated_profile = manager.get_profile("test_user")
    print(f"更新后的兴趣: {updated_profile['interests']}")

    # 3. 添加阅读历史
    print("\n3. 添加阅读历史:")
    manager.add_to_history(
        item_id="12345",
        title="Rust 1.80 发布",
        topic="Programming Languages",
        user_id="test_user"
    )
    history = manager.get_reading_history("test_user", limit=5)
    print(f"阅读历史 ({len(history)} 条):")
    for entry in history:
        print(f"  - {entry['title']} ({entry['topic']})")

    # 4. 更新偏好设置
    print("\n4. 更新偏好设置:")
    manager.update_preference("min_score", 50, "test_user")
    profile = manager.get_profile("test_user")
    print(f"最低分数: {profile['preferences']['min_score']}")


def test_summary_agent():
    """测试摘要 Agent。"""
    print("\n" + "=" * 60)
    print("测试 3: SummaryAgent - 文章深度解读")
    print("=" * 60)

    agent = SummaryAgent()

    # 测试文章
    test_title = "Understanding RAG Systems"
    test_content = """
    Retrieval-Augmented Generation (RAG) is a technique that combines the power of large language models
    with external knowledge retrieval. This approach allows AI systems to access up-to-date information
    and provide more accurate responses.

    Key benefits of RAG:
    1. Reduced hallucinations by grounding responses in real data
    2. Ability to work with domain-specific knowledge
    3. Cost-effective compared to fine-tuning large models
    4. Easy to update knowledge base without retraining

    RAG systems typically consist of three components: a retriever, a vector database, and a generator.
    The retriever finds relevant documents, which are then used by the generator to produce contextual responses.
    """

    print(f"\n文章标题: {test_title}")
    print("正在生成摘要...")

    result = agent.summarize_article(test_title, test_content)

    print(f"\n摘要: {result.get('summary', 'N/A')}")
    print(f"\n关键要点:")
    for i, point in enumerate(result.get('key_points', []), 1):
        print(f"  {i}. {point}")
    print(f"\n技术亮点: {result.get('technical_highlights', 'N/A')}")
    print(f"\n潜在影响: {result.get('potential_impact', 'N/A')}")

    # 测试快速摘要
    print("\n\n测试快速摘要生成:")
    quick_summary = agent.generate_quick_summary(test_content, max_length=100)
    print(f"快速摘要: {quick_summary}")


def test_comment_analysis_agent():
    """测试评论分析 Agent。"""
    print("\n" + "=" * 60)
    print("测试 4: CommentAnalysisAgent - 评论区分析")
    print("=" * 60)

    agent = CommentAnalysisAgent()

    # 测试评论数据
    test_comments = """
    [user1 (score: 45)]: This is a great article! RAG has been transformative for our product.
    We reduced hallucinations by 80% after implementing it.
      |- Reply by user2 (score: 12): How did you handle the latency issues?
      |- Reply by user1 (score: 8): We use caching and async processing.

    [user3 (score: 32)]: I'm skeptical about RAG. It seems like just fancy keyword search.
    The results are not always relevant.
      |- Reply by user4 (score: 15): You need to tune your embeddings and chunking strategy.

    [user5 (score: 28)]: One thing people miss is the cost. Vector databases aren't free,
    and embeddings add up quickly at scale.

    [user6 (score: 18)]: Has anyone tried hybrid search (dense + sparse)? We're seeing
    better results than pure semantic search.
    """

    print("\n正在分析评论区...")
    result = agent.analyze_comments(test_comments, "Understanding RAG Systems")

    print(f"\n核心争议点:")
    for controversy in result.get('controversies', []):
        print(f"  - {controversy}")

    print(f"\n社区主流观点:")
    opinion = result.get('mainstream_opinion', {})
    print(f"  情感: {opinion.get('sentiment', 'N/A')}")
    print(f"  总结: {opinion.get('summary', 'N/A')}")

    print(f"\n有价值的见解:")
    for insight in result.get('valuable_insights', []):
        print(f"  - {insight}")

    print(f"\n整体氛围: {result.get('overall_sentiment', 'N/A')}")


def test_recommendation_agent():
    """测试推荐 Agent。"""
    print("\n" + "=" * 60)
    print("测试 5: RecommendationAgent - 个性化推荐")
    print("=" * 60)

    # 注意：这个测试需要向量库中有数据
    # 如果向量库为空，会返回空推荐
    agent = RecommendationAgent()

    print("\n测试用户兴趣: ['AI/ML', 'Rust']")
    print("时间范围: 最近 7 天")
    print("正在生成推荐...")

    result = agent.recommend(
        interests=["AI/ML", "Rust"],
        days=7,
        top_k=3,
        min_score=0
    )

    print(f"\n{result.get('summary', 'N/A')}")

    recommendations = result.get('recommendations', [])
    if recommendations:
        print(f"\n推荐文章 ({len(recommendations)} 篇):")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec.get('title', 'N/A')}")
            print(f"   话题: {rec.get('topic', 'N/A')}")
            print(f"   分数: {rec.get('score', 0)}")
            print(f"   标签: {', '.join(rec.get('tags', []))}")
    else:
        print("\n提示: 向量库中暂无数据，推荐功能需要先运行爬虫并入库文章。")


def test_integration():
    """集成测试：完整工作流。"""
    print("\n" + "=" * 60)
    print("测试 6: 集成测试 - 完整工作流")
    print("=" * 60)

    # 1. 用户设置兴趣
    profile_manager = UserProfileManager()
    profile_manager.update_interests(["AI/ML", "Security/Privacy"], "demo_user")
    print("\n1. ✓ 用户兴趣已设置: ['AI/ML', 'Security/Privacy']")

    # 2. 路由查询
    router = QueryRouter()
    query = "最近 3 天的 AI 高分文章"
    routing_result = router.route_query(query)
    print(f"\n2. ✓ 查询路由完成: {query}")
    print(f"   过滤条件: {routing_result['filter']}")

    # 3. 推荐文章（需要向量库有数据）
    rec_agent = RecommendationAgent()
    recommendations = rec_agent.recommend(["AI/ML"], days=7, top_k=3)
    print(f"\n3. ✓ 推荐生成完成")
    print(f"   {recommendations.get('summary', 'N/A')}")

    # 4. 如果有推荐，分析第一篇文章
    if recommendations.get('recommendations'):
        first_rec = recommendations['recommendations'][0]
        item_id = first_rec.get('item_id')

        if item_id:
            # 生成摘要
            summary_agent = SummaryAgent()
            summary = summary_agent.summarize_by_id(item_id)
            print(f"\n4. ✓ 文章摘要生成完成")
            print(f"   {summary.get('summary', 'N/A')[:100]}...")

            # 分析评论
            comment_agent = CommentAnalysisAgent()
            comments = comment_agent.analyze_article_comments(item_id)
            print(f"\n5. ✓ 评论区分析完成")
            print(f"   整体氛围: {comments.get('overall_sentiment', 'N/A')}")

            # 更新阅读历史
            profile_manager.add_to_history(
                item_id=item_id,
                title=first_rec.get('title', 'Unknown'),
                topic=first_rec.get('topic', 'Unknown'),
                user_id="demo_user"
            )
            print(f"\n6. ✓ 阅读历史已更新")

    print("\n" + "=" * 60)
    print("集成测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("第三阶段 Agent 测试套件")
    print("=" * 60)

    try:
        # 运行所有测试
        test_query_router()
        test_user_profile()
        test_summary_agent()
        test_comment_analysis_agent()
        test_recommendation_agent()
        test_integration()

        print("\n\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

        print("\n提示:")
        print("- 如果推荐功能返回空结果，请先运行爬虫入库文章")
        print("- 运行爬虫: venv/bin/python -m app.crawler.crawler -n 30")
        print("- 运行向量化入库: venv/bin/python test_vector_pipeline.py")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
