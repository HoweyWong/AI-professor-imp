import asyncio
import json
import os
from typing import Literal
from urllib import error, request

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.documents import save_document

app = FastAPI(title="RAG-CMS API", version="0.1.0")


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rag-cms-api"}


@app.post("/v1/documents", status_code=201)
async def upload_document(file: UploadFile) -> dict[str, object]:
    return await save_document(file)


@app.post("/v1/chat/completions")
async def chat_completion(chat: ChatRequest) -> dict:
    base_url, api_key, model = configured_model()
    payload = {"model": model, "messages": [message.model_dump() for message in chat.messages], "temperature": chat.temperature}
    return await asyncio.to_thread(invoke_model, payload, base_url, api_key)
