# CMS 技术文档智能问答系统

## 目标

面向 CMS 需求书、设计文档、会议纪要和技术标准，提供带引用来源的智能问答能力。

## 学习文档

- [RAG-CMS 实现解读｜Java / Spring 开发者视角](RAG-CMS-Java开发者实现解读.md)：从领域对象、接口链路、文件存储、Embedding、向量检索、Prompt、引用、测试和 Spring Boot 演进路线理解当前代码。

## 首期范围

- 文档上传：PDF、Word、Markdown 或文本
- 文本解析与切分
- Embedding 与向量检索
- 基于检索上下文生成答案
- 返回引用来源
- Java 业务系统调用
- 问答日志

## 当前可运行功能

- `GET /health`：服务健康检查；
- `POST /v1/documents`：上传并解析 UTF-8 编码的 Markdown 或文本文件；
- `POST /v1/documents/{document_id}/chunks`：按固定长度和重叠窗口创建可追溯文本片段；
- `POST /v1/documents/{document_id}/embeddings`：调用兼容 OpenAI Embeddings API 的模型，并将向量保存到本地；
- `POST /v1/documents/{document_id}/questions`：检索相似 Chunk、调用模型生成回答，并返回可追溯引用；
- `POST /v1/chat/completions`：调用兼容 OpenAI Chat Completions API 的上游模型服务；
- 未配置模型环境变量时，问答接口返回明确的 `503`，不会发送外部请求。

上传接口将原文件、提取后的文本和元数据保存到项目根目录的 `data/documents/<document_id>/`，即默认位于 `RAG-CMS/data/documents/`，与服务从哪个目录启动无关。数据目录已被 Git 忽略。可通过 `RAG_CMS_DATA_DIR` 覆盖：绝对路径会直接使用，相对路径则以项目根目录为基准。当前仅支持 `.md`、`.markdown` 和 `.txt`，文件最大 5 MiB。

## 本地启动

首次初始化：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中填写模型配置后，后续每次启动只需执行：

```bash
./start.sh
```

该脚本会自动激活虚拟环境、加载 `.env` 并以热重载模式启动服务。可将 Uvicorn 参数直接传给脚本，例如：

```bash
./start.sh --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

模型配置需要填写 `.env` 中的 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 和 `EMBEDDING_MODEL`。调用问答接口会把检索到的文档片段发送给已配置的模型服务；只应使用已获批准处理这些文档的服务。`.env` 已被 Git 忽略，不应提交密钥。

完成文档上传、切分和向量化后，可对单个文档提问：

```bash
curl -X POST http://127.0.0.1:8000/v1/documents/10da35e7-0b7b-4541-9d95-dc70dffc5240/questions \
  -H 'Content-Type: application/json' \
  -d '{"question":"这份文档的发布前置条件是什么？","top_k":3}'
```

响应包含 `answer` 和 `citations`。每条引用提供文档 ID、Chunk 序号、原始文件路径、字符偏移及相似度；模型回答会使用 `[来源 N]` 与引用列表对应。问答只使用该文档检索出的上下文，找不到依据时应明确说明。

## 暂不做

- 多租户权限隔离
- 混合检索与 Rerank
- 管理后台
- 复杂 Agent 编排
- 本地模型部署

## 本地评测

`evals/week-02-cases.json` 保存 10 个机器可读评测用例。每题包含问题、期望答案要点、人工标注的相关 Chunk，以及一组或多组充分证据集合。充分证据集合中的任意一组被完整命中时，检索上下文即具备回答该题的最低证据；`app/evaluation.py` 会校验其格式和它与相关 Chunk 的包含关系，并提供不依赖网络的 `recall_at_k` 与宏平均 `mean_recall_at_k` 纯函数。

当前 Recall@K 只衡量检索结果覆盖了多少人工标注的相关 Chunk，不代表回答正确率或引用忠实性。运行相关单元测试：

```bash
.venv/bin/python -m unittest tests.test_evaluation -v
```

为固定语料完成上传、切分和向量化后，可以运行真实检索评测。命令只调用 Embedding，不调用回答模型：

```bash
set -a
source .env
set +a
.venv/bin/python -m app.eval_retrieval \
  --document-id 10da35e7-0b7b-4541-9d95-dc70dffc5240 \
  --k 1 3
```

输出包含每题的相关 Chunk、实际检索顺序、Recall@1、Recall@3 及宏平均汇总。文档 ID 是本地运行数据，实际使用时替换为当前固定语料对应的 ID。

## 建议技术栈

- Python：FastAPI、Pydantic、pytest
- Java：Spring Boot
- 数据库：PostgreSQL 或 MySQL
- 向量库：首期选择一种简单方案
- 部署：Docker Compose（待 Docker 环境就绪后接入）

## 首期验收标准

1. 能上传并解析一份文档；
2. 能完成切分和向量入库；
3. 能根据问题检索相关内容并生成答案；
4. 答案包含引用来源；
5. Java 端能够调用 Python 服务；
6. 有至少 10 个初始评测问题。
