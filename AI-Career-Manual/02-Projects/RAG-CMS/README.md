# CMS 技术文档智能问答系统

## 目标

面向 CMS 需求书、设计文档、会议纪要和技术标准，提供带引用来源的智能问答能力。

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
- `POST /v1/chat/completions`：调用兼容 OpenAI Chat Completions API 的上游模型服务；
- 未配置模型环境变量时，问答接口返回明确的 `503`，不会发送外部请求。

上传接口将原文件、提取后的文本和元数据保存到 `data/documents/<document_id>/`。数据目录已被 Git 忽略。当前仅支持 `.md`、`.markdown` 和 `.txt`，文件最大 5 MiB。

## 本地启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

模型配置需要填写 `.env` 中的 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`。`.env` 已被 Git 忽略，不应提交密钥。

## 暂不做

- 多租户权限隔离
- 混合检索与 Rerank
- 管理后台
- 复杂 Agent 编排
- 本地模型部署

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
