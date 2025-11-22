"""
快速测试 GLM-4 API 连接和功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.llm import get_llm, get_embeddings
from app.core.logger import logger


def test_llm():
    """测试 LLM 连接。"""
    print("\n" + "=" * 60)
    print("测试 GLM-4 LLM 连接")
    print("=" * 60)

    try:
        llm = get_llm(temperature=0.7)

        # 简单测试
        response = llm.invoke("你好，请用一句话介绍你自己。")
        print(f"\n✅ LLM 响应成功!")
        print(f"回答: {response.content}")
        return True

    except Exception as e:
        print(f"\n❌ LLM 测试失败: {e}")
        return False


def test_embeddings():
    """测试 Embeddings 连接。"""
    print("\n" + "=" * 60)
    print("测试 GLM-4 Embeddings 连接")
    print("=" * 60)

    try:
        embeddings = get_embeddings()

        # 简单测试
        test_text = "这是一个测试文本"
        result = embeddings.embed_query(test_text)

        print(f"\n✅ Embeddings 响应成功!")
        print(f"向量维度: {len(result)}")
        print(f"向量前5个值: {result[:5]}")
        return True

    except Exception as e:
        print(f"\n❌ Embeddings 测试失败: {e}")
        print(f"\n提示: GLM-4 的 embedding 模型名称可能需要调整")
        print(f"请查看智谱 AI 文档确认正确的模型名称")
        return False


if __name__ == "__main__":
    print("\n🧪 GLM-4 API 功能测试")
    print("=" * 60)

    # 测试 LLM
    llm_ok = test_llm()

    # 测试 Embeddings
    emb_ok = test_embeddings()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"LLM 测试: {'✅ 通过' if llm_ok else '❌ 失败'}")
    print(f"Embeddings 测试: {'✅ 通过' if emb_ok else '❌ 失败'}")

    if llm_ok and emb_ok:
        print("\n🎉 所有测试通过！可以正常使用应用。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和 API 密钥。")
