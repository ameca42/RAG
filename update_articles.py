"""
更新文章向量入库脚本 - 支持强制更新已有文章的向量数据。
"""

import sys
import os
import json
import argparse
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.chains.document_processor import DocumentProcessor
from app.chains.vector_pipeline import VectorPipeline
from app.core.logger import logger


class UpdateVectorPipeline(VectorPipeline):
    """扩展的向量管道，支持强制更新。"""

    def __init__(self, collection_name: str = "hacker_news"):
        """
        初始化更新向量管道。

        Args:
            collection_name: ChromaDB 集合名称
        """
        super().__init__(collection_name)
        self.force_update = False

    def set_force_update(self, force: bool = True):
        """设置是否强制更新已有文章。"""
        self.force_update = force
        logger.info(f"Force update mode: {'enabled' if force else 'disabled'}")

    def ingest_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        强制更新版本的文章入库。

        Args:
            article: Article dictionary from storage

        Returns:
            Dictionary with ingestion stats
        """
        item_id = article.get("item_id")
        title = article.get("title", "")

        if not item_id:
            logger.error("Article missing item_id, skipping ingestion")
            return {"error": "missing_item_id", "ingested": 0}

        # 在强制更新模式下，先删除已有的文档
        if self.force_update:
            self._remove_existing_documents(item_id)
        else:
            # 检查文章是否已存在（原版逻辑）
            if self.vector_store.check_exists(item_id, "article"):
                logger.info(f"Article {item_id} already exists in vector store, skipping (use --force to update)")
                return {"status": "skipped", "ingested": 0, "item_id": item_id}

        try:
            # 处理文章为文档
            documents = self.doc_processor.process_article(article)

            if not documents:
                logger.warning(f"No documents created for article '{title[:50]}...'")
                return {"status": "no_documents", "ingested": 0, "item_id": item_id}

            # 添加到向量库
            doc_ids = self.vector_store.add_documents(documents)

            action = "updated" if self.force_update else "ingested"
            logger.success(
                f"Successfully {action} article '{title[:50]}...' "
                f"({len(documents)} documents, {len(doc_ids)} IDs)"
            )

            return {
                "status": "success",
                "ingested": len(documents),
                "item_id": item_id,
                "doc_ids": doc_ids,
                "updated": self.force_update
            }

        except Exception as e:
            logger.error(f"Error processing article {item_id}: {e}")
            return {"error": str(e), "ingested": 0, "item_id": item_id}

    def _remove_existing_documents(self, item_id: str):
        """
        删除指定文章的所有文档。

        Args:
            item_id: 文章ID
        """
        try:
            # 获取所有匹配的文档
            results = self.vector_store.similarity_search(
                query="",  # 空查询，通过metadata过滤
                k=1000,  # 获取大量结果
                filter_dict={"item_id": item_id}
            )

            if results:
                # 提取文档ID
                doc_ids = [doc.metadata.get("doc_id") for doc in results if doc.metadata.get("doc_id")]

                if doc_ids:
                    # 删除文档
                    self.vector_store.collection.delete(ids=doc_ids)
                    logger.info(f"Removed {len(doc_ids)} existing documents for article {item_id}")
            else:
                logger.info(f"No existing documents found for article {item_id}")

        except Exception as e:
            logger.warning(f"Error removing existing documents for article {item_id}: {e}")

    def update_batch(self, articles: list, force: bool = False) -> Dict[str, Any]:
        """
        批量更新文章到向量库。

        Args:
            articles: 文章列表
            force: 是否强制更新已有文章

        Returns:
            统计信息
        """
        self.force_update = force

        if not articles:
            logger.warning("No articles to update")
            return {"total": 0, "updated": 0, "skipped": 0, "errors": 0}

        stats = {
            "total": len(articles),
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "docs_created": 0
        }

        action_word = "updating" if force else "ingesting"
        logger.info(f"Starting batch {action_word} of {len(articles)} articles")

        for article in articles:
            try:
                result = self.ingest_article(article)

                if result["status"] == "success":
                    if result.get("updated"):
                        stats["updated"] += 1
                    else:
                        stats["updated"] += 1  # 新文章也算更新
                    stats["docs_created"] += result["ingested"]
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                stats["errors"] += 1
                continue

        logger.success(
            f"Batch update complete: {stats['updated']} updated, "
            f"{stats['skipped']} skipped, {stats['errors']} errors, "
            f"{stats['docs_created']} docs created"
        )

        return stats


def main():
    """主函数：批量更新文章到向量库。"""
    parser = argparse.ArgumentParser(description="更新文章向量数据")
    parser.add_argument("--article-id", type=int, help="只更新指定ID的文章")
    parser.add_argument("--topic", type=str, help="只更新指定话题的文章")
    parser.add_argument("--force", action="store_true", help="强制更新已有文章")
    parser.add_argument("--recent", type=int, help="只更新最近N篇文章")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔄 文章向量更新脚本")
    print("=" * 60)

    # 1. 加载文章数据
    articles_file = "data/articles.json"

    if not os.path.exists(articles_file):
        print(f"❌ 文件不存在: {articles_file}")
        print("请先运行爬虫: python -m app.crawler.crawler -n 30")
        return

    print(f"\n1. 加载文章数据...")
    with open(articles_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"   找到 {len(articles)} 篇文章")

    # 2. 筛选文章
    if args.article_id:
        articles = [a for a in articles if a.get("item_id") == args.article_id]
        print(f"   筛选到 {len(articles)} 篇文章 (ID: {args.article_id})")
    elif args.topic:
        articles = [a for a in articles if a.get("topic") == args.topic]
        print(f"   筛选到 {len(articles)} 篇文章 (话题: {args.topic})")
    elif args.recent:
        # 按分数排序，取最近的N篇
        articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)[:args.recent]
        print(f"   筛选到 {len(articles)} 篇文章 (最近 {args.recent} 篇)")

    if not articles:
        print("❌ 没有找到符合条件的文章")
        return

    # 3. 初始化向量管道
    print(f"\n2. 初始化向量管道...")
    print(f"   强制更新模式: {'启用' if args.force else '禁用'}")

    pipeline = UpdateVectorPipeline()
    pipeline.set_force_update(args.force)

    # 4. 批量更新
    print(f"\n3. 开始批量更新...")
    print(f"   这可能需要几分钟，请耐心等待...")

    try:
        result = pipeline.update_batch(articles, force=args.force)

        print(f"\n✅ 更新完成！")
        print(f"=" * 60)
        print(f"总文章数: {result['total']}")
        print(f"成功更新: {result['updated']}")
        print(f"跳过: {result['skipped']}")
        print(f"失败: {result['errors']}")
        print(f"文档数（含chunk）: {result['docs_created']}")
        print(f"=" * 60)

        if result['errors'] > 0:
            print(f"\n⚠️  {result['errors']} 篇文章更新失败，请检查日志")

    except Exception as e:
        print(f"\n❌ 批量更新失败: {e}")
        import traceback
        traceback.print_exc()

    # 5. 查看统计
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