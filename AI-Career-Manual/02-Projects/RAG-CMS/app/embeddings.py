import json
import os
from urllib import error, request

from fastapi import HTTPException

BATCH_SIZE = 100


def embedding_settings() -> tuple[str, str, str]:
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("EMBEDDING_MODEL", "")
    if not all((base_url, api_key, model)):
        raise HTTPException(503, "Embedding 服务未配置；请设置 LLM_BASE_URL、LLM_API_KEY 和 EMBEDDING_MODEL")
    return base_url, api_key, model


def invoke_embedding_batch(texts: list[str], base_url: str, api_key: str, model: str) -> list[list[float]]:
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    upstream = request.Request(
        f"{base_url}/embeddings", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with request.urlopen(upstream, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise HTTPException(502, f"Embedding 服务返回 HTTP {exc.code}") from exc
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Embedding 服务调用失败") from exc

    if not isinstance(payload, dict):
        raise HTTPException(502, "Embedding 服务返回了无效响应")
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise HTTPException(502, "Embedding 服务返回的向量数量异常")
    vectors = [item.get("embedding") for item in sorted(data, key=lambda item: item.get("index", 0))]
    if not all(isinstance(vector, list) and vector for vector in vectors):
        raise HTTPException(502, "Embedding 服务返回了无效向量")
    if not all(all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in vector) for vector in vectors):
        raise HTTPException(502, "Embedding 服务返回了非数值向量")
    return [[float(value) for value in vector] for vector in vectors]


def embed_texts(texts: list[str]) -> tuple[str, list[list[float]]]:
    if not texts:
        raise HTTPException(409, "文档尚未生成可向量化的文本片段")
    base_url, api_key, model = embedding_settings()
    vectors: list[list[float]] = []
    for offset in range(0, len(texts), BATCH_SIZE):
        vectors.extend(invoke_embedding_batch(texts[offset:offset + BATCH_SIZE], base_url, api_key, model))
    dimensions = len(vectors[0])
    if any(len(vector) != dimensions for vector in vectors):
        raise HTTPException(502, "Embedding 服务返回的向量维度不一致")
    return model, vectors
