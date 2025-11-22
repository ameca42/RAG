"""
完整的 GLM-4 API 和向量存储测试。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.llm import get_llm, get_embeddings
from app.db.vector_store import VectorStoreManager
from app.core.logger import logger


def test_1_llm():
    """测试 LLM 连接。"""
    print("\n" + "=" * 60)
    print("测试 1: GLM-4 LLM 连接")
    print("=" * 60)

    try:
        llm = get_llm(temperature=0.7)
        response = llm.invoke("用一句话介绍你自己")
        print(f"✅ LLM 测试通过")
        print(f"   回答: {response.content[:50]}...")
        return True
    except Exception as e:
        print(f"❌ LLM 测试失败: {e}")
        return False


def test_2_embeddings():
    """测试 Embeddings 连接。"""
    print("\n" + "=" * 60)
    print("测试 2: GLM-4 Embeddings 连接")
    print("=" * 60)

    try:
        embeddings = get_embeddings()
        result = embeddings.embed_query("测试文本")
        print(f"✅ Embeddings 测试通过")
        print(f"   向量维度: {len(result)}")
        return True
    except Exception as e:
        print(f"❌ Embeddings 测试失败: {e}")
        return False


def test_3_vector_store():
    """测试向量存储初始化。"""
    print("\n" + "=" * 60)
    print("测试 3: VectorStoreManager 初始化")
    print("=" * 60)

    try:
        vm = VectorStoreManager()
        stats = vm.get_collection_stats()
        print(f"✅ VectorStoreManager 初始化成功")
        print(f"   集合名称: {stats['collection_name']}")
        print(f"   文档数量: {stats['total_documents']}")
        print(f"   使用模型: {vm.embeddings.model}")
        return True
    except Exception as e:
        print(f"❌ VectorStoreManager 初始化失败: {e}")
        return False


def test_4_empty_query():
    """测试空查询处理（GLM-4 特有问题）。"""
    print("\n" + "=" * 60)
    print("测试 4: 空查询处理（GLM-4 特有）")
    print("=" * 60)

    try:
        vm = VectorStoreManager()

        # 测试空查询
        results = vm.similarity_search("", k=5)
        print(f"✅ 空查询测试通过（返回 {len(results)} 个结果）")

        # 测试空白查询
        results = vm.similarity_search("   ", k=5)
        print(f"✅ 空白查询测试通过（返回 {len(results)} 个结果）")

        return True
    except Exception as e:
        print(f"❌ 空查询测试失败: {e}")
        return False


def test_5_normal_query():
    """测试正常查询。"""
    print("\n" + "=" * 60)
    print("测试 5: 正常查询")
    print("=" * 60)

    try:
        vm = VectorStoreManager()
        results = vm.similarity_search("AI 人工智能", k=3)
        print(f"✅ 正常查询测试通过（返回 {len(results)} 个结果）")
        return True
    except Exception as e:
        print(f"❌ 正常查询测试失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 GLM-4 完整功能测试套件")
    print("=" * 60)

    tests = [
        ("LLM 连接", test_1_llm),
        ("Embeddings 连接", test_2_embeddings),
        ("VectorStore 初始化", test_3_vector_store),
        ("空查询处理", test_4_empty_query),
        ("正常查询", test_5_normal_query),
    ]

    results = []
    for name, test_func in tests:
        results.append((name, test_func()))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！应用可以正常使用。")
        print("\n下一步:")
        print("1. 运行爬虫: venv/bin/python -m app.crawler.crawler -n 30")
        print("2. 向量化入库: venv/bin/python test_vector_pipeline.py")
        print("3. 启动应用: ./start_app.sh")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查配置。")
