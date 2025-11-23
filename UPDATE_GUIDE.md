# 文章向量更新指南

## 脚本说明

`update_articles.py` 是一个增强版的向量入库脚本，支持**强制更新**已有文章的向量数据。

## 主要功能

1. **强制更新**: 可以更新已存在于向量库中的文章
2. **精确筛选**: 支持按文章ID、话题、最新文章等条件筛选
3. **批量处理**: 支持批量更新多篇文章
4. **安全删除**: 更新前先删除旧的向量数据，避免重复

## 使用方法

### 基本语法
```bash
python update_articles.py [选项]
```

### 常用选项

#### 1. 更新特定文章
```bash
# 更新单篇文章（我们刚才修复的评论文章）
python update_articles.py --article-id 46009660 --force

# 更新多篇文章
python update_articles.py --article-id 46009660 --article-id 46020151 --force
```

#### 2. 按话题更新
```bash
# 更新所有AI/ML相关的文章
python update_articles.py --topic "AI/ML" --force

# 更新安全相关的文章
python update_articles.py --topic "Security/Privacy" --force
```

#### 3. 更新最新文章
```bash
# 更新最新的10篇文章
python update_articles.py --recent 10 --force

# 更新最新的20篇文章
python update_articles.py --recent 20 --force
```

#### 4. 全量更新（谨慎使用）
```bash
# 更新所有文章
python update_articles.py --force
```

## 场景示例

### 场景1: 修复特定文章的数据
当我们修复了某篇文章的评论数据后：
```bash
python update_articles.py --article-id 46009660 --force
```

### 场景2: 修复所有高分文章
先找出高分文章，然后批量更新：
```bash
# 获取最近的高分文章并更新前20篇
python update_articles.py --recent 20 --force
```

### 场景3: 修复特定话题的文章
如果发现某个话题的文章数据有问题：
```bash
# 修复所有AI/ML文章
python update_articles.py --topic "AI/ML" --force
```

## 重要选项说明

### `--force` 标志
- **不使用 `--force`**: 默认行为，跳过已存在的文章（等同于原 `ingest_articles.py`）
- **使用 `--force`**: 强制更新已存在的文章，先删除旧数据再重新添加

### 筛选条件
- **`--article-id`**: 指定文章ID，可以多次使用
- **`--topic`**: 指定话题名称
- **`--recent`**: 更新最新的N篇文章（按分数排序）

## 安全建议

1. **小批量测试**: 先用少量文章测试效果
   ```bash
   python update_articles.py --recent 2 --force
   ```

2. **备份数据**: 在大规模更新前，可以备份 ChromaDB 数据
   ```bash
   cp -r data/chromadb data/chromadb.backup.$(date +%Y%m%d_%H%M%S)
   ```

3. **检查日志**: 更新过程中注意检查日志输出，确保没有错误

## 输出示例

```
🔄 文章向量更新脚本
============================================================

1. 加载文章数据...
   找到 35 篇文章
   筛选到 1 篇文章 (ID: 46009660)

2. 初始化向量管道...
   强制更新模式: 启用

3. 开始批量更新...
   这可能需要几分钟，请耐心等待...
Removed 8 existing documents for article 46009660
Successfully updated article 'Is Matrix Multiplication Ugly?' (8 documents, 8 IDs)

✅ 更新完成！
============================================================
总文章数: 1
成功更新: 1
跳过: 0
失败: 0
文档数（含chunk）: 8
============================================================
```

## 注意事项

1. **性能影响**: 大批量更新会消耗较多计算资源
2. **网络依赖**: 更新过程需要访问 OpenAI API 进行向量化
3. **重复更新**: 不需要重复更新未修改的文章
4. **API限制**: 注意 OpenAI API 的调用频率限制

## 故障排除

### 常见问题

1. **内存不足**: 减少批次大小，分批更新
2. **API错误**: 检查 OpenAI API 配置和网络连接
3. **权限错误**: 确保对数据目录有写权限
4. **超时错误**: 可能是网络慢或文章内容过长

### 查看详细日志
```bash
# 设置日志级别为 DEBUG
export LOG_LEVEL=DEBUG
python update_articles.py --recent 5 --force
```

## 原版 vs 更新版对比

| 功能 | `ingest_articles.py` | `update_articles.py` |
|------|---------------------|----------------------|
| 新增文章 | ✅ | ✅ |
| 跳过重复 | ✅ | ✅ (默认) |
| 强制更新 | ❌ | ✅ |
| 精确筛选 | ❌ | ✅ |
| 批量删除 | ❌ | ✅ |
| 详细日志 | ❌ | ✅ |