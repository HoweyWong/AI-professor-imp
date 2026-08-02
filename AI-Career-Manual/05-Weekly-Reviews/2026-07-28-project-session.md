# 2026-07-28｜第 3 次项目时段记录

## 今日主目标

实现固定长度与重叠窗口的文本切分，为后续 Embedding 和向量检索构建带来源信息的 Chunk 数据。

## 完成结果

- [x] 新增 `app/chunks.py`
- [x] 新增 `POST /v1/documents/{document_id}/chunks`
- [x] 默认按 800 字符切分，默认重叠 120 字符
- [x] 在窗口内优先按换行或空格断开
- [x] 将切分结果保存为 `chunks.json`
- [x] 在 `metadata.json` 回写切分参数、片段数、路径和更新时间

## Chunk 元数据

每个片段包含：

- `document_id`
- `chunk_index`
- `content`
- `start_offset`（包含）
- `end_offset`（不包含）
- `source_path`

## 验证结果

```text
上传 README.md：1,398 字符
chunk_size=300，chunk_overlap=50
→ 生成 6 个 Chunk，序号为 0 至 5
→ chunks.json 与 metadata.json 均已保存

chunk_size=300，chunk_overlap=300
→ 422，拒绝无效重叠参数
```

## 今日最重要的一个知识点

RAG 的 Chunk 不是单纯的文本数组。每个片段必须保留来源、顺序和原始位置，才能支持引用回溯、错误定位、重建上下文和后续权限控制。

## 下一项目时段｜7月30日（周四）

为每个 Chunk 生成 Embedding，并接入一个最小向量存储实现。