"""Deterministic FastAPI contract server for the Java-to-Python integration test.

The HTTP route and response mapping are real. Embedding, retrieval, and model calls
are explicit local substitutes, so this module never sends document data outside.
"""

import os

from app import main as rag_main


def _embed_texts(texts: list[str]) -> tuple[str, list[list[float]]]:
    assert texts == ["发布前做什么？"]
    return "contract-embedding", [[1.0, 0.0]]


def _search_vectors(
    document_id: str,
    embedding_model: str,
    query_vector: list[float],
    top_k: int,
) -> list[dict[str, object]]:
    assert document_id == "contract-document"
    assert embedding_model == "contract-embedding"
    assert query_vector == [1.0, 0.0]
    assert top_k == 1
    return [
        {
            "document_id": document_id,
            "chunk_index": 2,
            "content": "发布前必须完成回归测试。",
            "source_path": "contract-document/source.md",
            "start_offset": 20,
            "end_offset": 34,
            "score": 0.91,
        }
    ]


def _invoke_model(payload: dict, base_url: str, api_key: str) -> dict:
    assert payload["model"] == "contract-model"
    assert "发布前必须完成回归测试。" in payload["messages"][1]["content"]
    assert base_url == "http://contract-model.invalid/v1"
    assert api_key == "contract-key"
    return {"choices": [{"message": {"content": "完成回归测试。[来源 1]"}}]}


os.environ["LLM_BASE_URL"] = "http://contract-model.invalid/v1"
os.environ["LLM_API_KEY"] = "contract-key"
os.environ["LLM_MODEL"] = "contract-model"

rag_main.embed_texts = _embed_texts
rag_main.search_vectors = _search_vectors
rag_main.invoke_model = _invoke_model

app = rag_main.app
