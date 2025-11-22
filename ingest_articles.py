"""
向量化入库脚本 - 将爬取的文章向量化并存入 ChromaDB。
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.chains.document_processor import DocumentProcessor
from app.chains.vector_pipeline import VectorPipeline
from app.core.logger import logger


def main():
    """主函数：批量导入文章到向量库。"""
    print("\n" + "=" * 60)
    print("📥 向量化入库脚本")
    print("=" * 60)

    # 1. 加载文章数据
    articles_file = "data/articles.json"

    if not os.path.exists(articles_file):
        print(f"❌ 文件不存在: {articles_file}")
        print("请先运行爬虫: venv/bin/python -m app.crawler.crawler -n 30")
        return

    print(f"\n1. 加载文章数据...")
    with open(articles_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get('articles', [])
    print(f"   找到 {len(articles)} 篇文章")

    if not articles:
        print("❌ 没有文章可以入库")
        return

    # 2. 初始化向量管道
    print(f"\n2. 初始化向量管道...")
    pipeline = VectorPipeline()

    # 3. 批量入库
    print(f"\n3. 开始批量入库...")
    print(f"   这可能需要几分钟，请耐心等待...")

    try:
        result = pipeline.ingest_batch(articles)

        print(f"\n✅ 入库完成！")
        print(f"=" * 60)
        print(f"总文章数: {result['total']}")
        print(f"新增文章: {result['ingested']}")
        print(f"已存在（跳过）: {result['skipped']}")
        print(f"失败: {result['errors']}")
        print(f"文档数（含chunk）: {result['docs_created']}")
        print(f"=" * 60)

        if result['errors'] > 0:
            print(f"\n⚠️  {result['errors']} 篇文章入库失败，请检查日志")

    except Exception as e:
        print(f"\n❌ 批量入库失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 查看统计
    print(f"\n4. 向量库统计:")
    stats = pipeline.get_stats()
    print(f"   集合名称: {stats.get('collection_name')}")
    print(f"   总文档数: {stats.get('total_documents')}")
    print(f"   文档类型: {stats.get('unique_doc_types')}")
    print(f"   话题数: {len(stats.get('unique_topics', []))}")

    print(f"\n🎉 完成！现在可以启动应用了:")
    print(f"   ./start_app.sh")


if __name__ == "__main__":
    main()
