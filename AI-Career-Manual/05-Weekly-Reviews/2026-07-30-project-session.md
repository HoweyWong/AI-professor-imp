# 2026-07-30｜第 4 次项目时段记录

## 今日主目标

为文档 Chunk 接入兼容 OpenAI Embeddings API 的调用接口，并构建可用于后续检索的最小本地向量存储。

## 完成结果

- [x] 新增 `app/embeddings.py`
- [x] 支持通过 `LLM_BASE_URL`、`LLM_API_KEY`、`EMBEDDING_MODEL` 调用 `/embeddings`
- [x] 每批最多处理 100 个 Chunk
- [x] 校验上游响应数量、向量维度和数值类型
- [x] 新增 `app/vectors.py`
- [x] 新增 `POST /v1/documents/{document_id}/embeddings`
- [x] 将向量保存到 `vectors.json`
- [x] 在 `metadata.json` 记录模型、向量数量、维度、路径和更新时间

## 验证结果

```text
未配置 Embedding 服务：
POST /v1/documents/{document_id}/embeddings
→ 503，不调用外部模型

本地模拟向量：
6 个 Chunk × 3 维向量
→ vectors.json 保存 6 条记录
→ metadata.json 的 vector_count=6，dimension=3
```

## 当前边界

- 未填入 `EMBEDDING_MODEL` 前，无法生成真实语义向量；
- 最小向量存储使用 JSON 文件，适合学习和小数据验证，不适合生产规模；
- 下一步需要实现余弦相似度检索、上下文拼接和带引用回答。

## 今日最重要的一个知识点

Embedding 模型、向量维度和向量存储必须一起记录。不同模型生成的向量通常不能直接混合检索，模型切换后需要重新向量化受影响的 Chunk。

## 下一项目时段｜8月1日（周六）

实现余弦相似度 Top-K 检索、上下文拼接、问答调用和引用来源返回。