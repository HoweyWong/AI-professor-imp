import asyncio
import json
import os
from typing import Literal
from urllib import error, request

from fastapi import FastAPI, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.chunks import create_chunks
from app.documents import save_document
from app.embeddings import embed_texts
from app.retrieval import search_vectors
from app.vectors import create_embeddings

app = FastAPI(title="RAG-CMS API", version="0.1.0")


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


def configured_model() -> tuple[str, str, str]:
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")
    if not all((base_url, api_key, model)):
        raise HTTPException(503, "模型服务未配置；请设置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL")
    return base_url, api_key, model


def invoke_model(payload: dict, base_url: str, api_key: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    upstream = request.Request(
        f"{base_url}/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with request.urlopen(upstream, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise HTTPException(502, f"模型服务返回 HTTP {exc.code}") from exc
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "模型服务调用失败") from exc


def answer_text(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(502, "模型服务返回了无效回答") from exc
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(502, "模型服务返回了空回答")
    return content.strip()


def build_question_messages(question: str, matches: list[dict[str, object]]) -> list[dict[str, str]]:
    context_parts = [
        f"[来源 {index}] 文件：{match['source_path']}；片段：{match['chunk_index']}\n{match['content']}"
        for index, match in enumerate(matches, start=1)
    ]
    context = "\n\n".join(context_parts)
    return [
        {
            "role": "system",
            "content": (
                "你是 CMS 技术文档问答助手。只能依据给定上下文回答；"
                "无法确定时明确说明。回答中的事实使用 [来源 N] 标注。"
            ),
        },
        {"role": "user", "content": f"上下文：\n{context}\n\n问题：{question}"},
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rag-cms-api"}


@app.post("/v1/documents", status_code=201)
async def upload_document(file: UploadFile) -> dict[str, object]:
    return await save_document(file)


@app.post("/v1/documents/{document_id}/chunks")
def chunk_document(
    document_id: str,
    chunk_size: int = Query(default=800, ge=100, le=4000),
    chunk_overlap: int = Query(default=120, ge=0, le=1000),
) -> dict[str, object]:
    return create_chunks(document_id, chunk_size, chunk_overlap)


@app.post("/v1/documents/{document_id}/embeddings")
def embed_document(document_id: str) -> dict[str, object]:
    return create_embeddings(document_id)


@app.post("/v1/documents/{document_id}/questions")
async def ask_document(document_id: str, query: QuestionRequest) -> dict[str, object]:
    question = query.question.strip()
    if not question:
        raise HTTPException(422, "问题不能只包含空白字符")

    embedding_model, vectors = await asyncio.to_thread(embed_texts, [question])
    matches = search_vectors(document_id, embedding_model, vectors[0], query.top_k)
    if not matches:
        raise HTTPException(409, "没有检索到可用于回答的文档片段")

    base_url, api_key, model = configured_model()
    payload = {
        "model": model,
        "messages": build_question_messages(question, matches),
        "temperature": 0.2,
    }
    response = await asyncio.to_thread(invoke_model, payload, base_url, api_key)
    citations = [
        {
            "reference": index,
            "document_id": match["document_id"],
            "chunk_index": match["chunk_index"],
            "source_path": match["source_path"],
            "start_offset": match["start_offset"],
            "end_offset": match["end_offset"],
            "score": match["score"],
        }
        for index, match in enumerate(matches, start=1)
    ]
    return {"document_id": document_id, "question": question, "answer": answer_text(response), "citations": citations}


@app.post("/v1/chat/completions")
async def chat_completion(chat: ChatRequest) -> dict:
    base_url, api_key, model = configured_model()
    payload = {"model": model, "messages": [message.model_dump() for message in chat.messages], "temperature": chat.temperature}
    return await asyncio.to_thread(invoke_model, payload, base_url, api_key)
