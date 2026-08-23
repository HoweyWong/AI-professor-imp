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

`evals/week-02-cases.json` 保存 10 个机器可读评测用例。每题包含问题、期望答案要点、人工标注的相关 Chunk，以及一组或多组充分证据集合。充分证据集合中的任意一组被完整命中时，检索上下文即具备回答该题的最低证据；`app/evaluation.py` 会校验其格式和它与相关 Chunk 的包含关系，并提供不依赖网络的 Recall@K、充分证据命中及宏平均纯函数。

`evals/week-03-manual-scores.json` 保存 2026-08-02 与 2026-08-04 基线回答的人工评分。`covered_point_indexes` 标记已覆盖的期望要点，由程序计算覆盖率；`citation_faithful` 和 `unsupported_claims` 分别记录引用忠实性及无依据主张。加载时要求人工评分完整覆盖全部评测用例。程序只校验并汇总人工判断，不会把它伪装成自动客观评分。

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
  --k 1 3 \
  --manual-scores evals/week-03-manual-scores.json
```

输出包含每题的相关 Chunk、充分证据集合、实际检索顺序、Recall@1/3、充分证据命中@1/3、人工答案要点覆盖、引用忠实性及汇总。充分证据命中是布尔指标：Top-K 完整包含任意一组充分证据时为 `1`，否则为 `0`。不传 `--manual-scores` 时只生成检索层报告，避免把旧回答的人工评分错误绑定到新的评测运行。文档 ID 是本地运行数据，实际使用时替换为当前固定语料对应的 ID。

若外部 Embedding 服务不可用或不获准接收评测问题，可重放已保存的真实检索快照。快照绑定语料哈希、用例哈希、Chunk 参数、Embedding 模型、文档 ID 和原始运行记录；此模式不会发送外部请求：

```bash
.venv/bin/python -m app.eval_retrieval \
  --document-id 10da35e7-0b7b-4541-9d95-dc70dffc5240 \
  --k 1 3 \
  --manual-scores evals/week-03-manual-scores.json \
  --retrieval-snapshot evals/week-03-retrieval-snapshot.json \
  --output evals/week-03-complete-report.json
```

离线重放验证的是“保存的真实检索结果在当前 Ground Truth 和评分规则下会得到什么报告”，不能证明当前外部 Embedding 服务仍会返回相同顺序。需要比较模型或参数变化时，必须在目标服务获得明确授权后重新运行在线评测并生成新的快照。

## Java 调用

`java-client/` 提供面向 Java 11、Spring Boot 2.7.18 的最小 `WebClient` 客户端。它将问题和 `top_k` 发送给文档问答接口，并把答案及引用映射为 DTO；502、503、超时和一般传输故障会映射为不同的 `FailureType`。

```java
RagCmsClient client = new RagCmsClient(
        "http://127.0.0.1:8000",
        Duration.ofSeconds(35)
);
QuestionResponse response = client.ask(documentId, "发布前要做什么？", 3);
```

运行 Java 本地契约测试：

```bash
cd java-client
mvn test
```

测试使用 `127.0.0.1` 随机端口上的临时假服务，不调用 Python、Embedding 或回答模型。它验证 JSON 契约和错误边界，不代表真实 RAG 链路已经完成端到端验收。

进一步验证 Java 客户端与真实 FastAPI 路由的契约时，在 RAG-CMS 根目录启动明确的本地替身服务：

```bash
LLM_BASE_URL=http://contract-model.invalid/v1 \
LLM_API_KEY=contract-key \
LLM_MODEL=contract-model \
.venv/bin/python -m uvicorn tests.contract_server:app --host 127.0.0.1 --port 18080
```

另开终端运行 Java→Python 契约测试：

```bash
cd java-client
RAG_CMS_CONTRACT_BASE_URL=http://127.0.0.1:18080 \
  mvn -q -Dtest=RagCmsPythonContractTest test
```

该测试会穿过真实 HTTP、FastAPI 路由、请求校验、Prompt 构造、响应和 Java DTO 映射；`tests/contract_server.py` 明确替换 Embedding、检索和回答模型，因此不会访问外部服务，也不能证明真实模型、真实向量或真实数据授权已经通过验收。

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
