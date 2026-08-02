import json
from datetime import datetime, timezone

from fastapi import HTTPException

from app.chunks import document_directory
from app.embeddings import embed_texts


def load_chunks(document_id: str) -> tuple[object, list[dict[str, object]]]:
    directory = document_directory(document_id)
    chunks_path = directory / "chunks.json"
    if not chunks_path.is_file():
        raise HTTPException(409, "请先为文档创建文本片段")
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    if not isinstance(chunks, list) or not chunks:
        raise HTTPException(409, "文档没有可用的文本片段")
    return directory, chunks


def save_vectors(document_id: str, model: str, vectors: list[list[float]]) -> dict[str, object]:
    directory, chunks = load_chunks(document_id)
    if len(chunks) != len(vectors):
        raise HTTPException(502, "文本片段与向量数量不一致")
    dimension = len(vectors[0]) if vectors else 0
    if not dimension or any(len(vector) != dimension for vector in vectors):
        raise HTTPException(502, "向量维度不一致")

    records = [
        {
            "document_id": document_id,
            "chunk_index": chunk["chunk_index"],
            "source_path": chunk["source_path"],
            "vector": vector,
        }
        for chunk, vector in zip(chunks, vectors)
    ]
    vectors_path = directory / "vectors.json"
    vectors_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    metadata_path = directory / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["vector_store"] = {
        "model": model,
        "vector_count": len(records),
        "dimension": dimension,
        "vectors_path": f"{document_id}/vectors.json",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"document_id": document_id, **metadata["vector_store"]}


def create_embeddings(document_id: str) -> dict[str, object]:
    _, chunks = load_chunks(document_id)
    texts = [str(chunk["content"]) for chunk in chunks]
    model, vectors = embed_texts(texts)
    return save_vectors(document_id, model, vectors)
