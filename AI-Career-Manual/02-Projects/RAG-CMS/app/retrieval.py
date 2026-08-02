import json
from math import sqrt

from fastapi import HTTPException

from app.vectors import load_chunks


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise HTTPException(409, "查询向量维度与文档向量维度不一致")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        raise HTTPException(422, "不能使用零向量进行检索")
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def search_vectors(
    document_id: str, embedding_model: str, query_vector: list[float], top_k: int
) -> list[dict[str, object]]:
    directory, chunks = load_chunks(document_id)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    vector_store = metadata.get("vector_store")
    if not isinstance(vector_store, dict):
        raise HTTPException(409, "请先为文档生成 Embedding")
    if vector_store.get("model") != embedding_model:
        raise HTTPException(409, "查询模型与文档向量模型不一致，请重新向量化文档")

    vectors_path = directory / "vectors.json"
    if not vectors_path.is_file():
        raise HTTPException(409, "文档向量文件不存在")
    records = json.loads(vectors_path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != len(chunks):
        raise HTTPException(409, "文档向量数据不完整")
    chunks_by_index = {chunk["chunk_index"]: chunk for chunk in chunks}
    matches: list[dict[str, object]] = []
    for record in records:
        chunk_index = record.get("chunk_index")
        chunk = chunks_by_index.get(chunk_index)
        vector = record.get("vector")
        if chunk is None or not isinstance(vector, list):
            raise HTTPException(409, "文档向量数据格式错误")
        matches.append({
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content": chunk["content"],
            "source_path": chunk["source_path"],
            "start_offset": chunk["start_offset"],
            "end_offset": chunk["end_offset"],
            "score": cosine_similarity(query_vector, vector),
        })
    return sorted(matches, key=lambda item: float(item["score"]), reverse=True)[:top_k]
