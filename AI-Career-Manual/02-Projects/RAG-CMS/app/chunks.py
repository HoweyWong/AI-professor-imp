import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.documents import data_directory


def document_directory(document_id: str) -> Path:
    try:
        UUID(document_id)
    except ValueError as exc:
        raise HTTPException(404, "文档不存在") from exc
    directory = data_directory() / document_id
    if not (directory / "content.txt").is_file():
        raise HTTPException(404, "文档不存在")
    return directory


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[dict[str, object]]:
    if chunk_overlap >= chunk_size:
        raise HTTPException(422, "chunk_overlap 必须小于 chunk_size")

    chunks: list[dict[str, object]] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            halfway = start + chunk_size // 2
            boundary = max(text.rfind("\n", halfway, end), text.rfind(" ", halfway, end))
            if boundary > start:
                end = boundary + 1
        content = text[start:end]
        if content.strip():
            chunks.append({"content": content, "start_offset": start, "end_offset": end})
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def create_chunks(document_id: str, chunk_size: int, chunk_overlap: int) -> dict[str, object]:
    directory = document_directory(document_id)
    text = (directory / "content.txt").read_text(encoding="utf-8")
    metadata_path = directory / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_path = str(metadata["source_path"])
    chunks = split_text(text, chunk_size, chunk_overlap)
    for index, chunk in enumerate(chunks):
        chunk.update({"document_id": document_id, "chunk_index": index, "source_path": source_path})

    chunks_path = directory / "chunks.json"
    chunks_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata["chunking"] = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "chunk_count": len(chunks),
        "chunks_path": f"{document_id}/chunks.json",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"document_id": document_id, **metadata["chunking"], "chunks": chunks}
