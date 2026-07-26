import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

ALLOWED_SUFFIXES = {".md", ".markdown", ".txt"}
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIRECTORY = PROJECT_DIRECTORY / "data" / "documents"


def data_directory() -> Path:
    configured_directory = os.getenv("RAG_CMS_DATA_DIR")
    if not configured_directory:
        return DEFAULT_DATA_DIRECTORY

    directory = Path(configured_directory).expanduser()
    return directory if directory.is_absolute() else PROJECT_DIRECTORY / directory


async def save_document(file: UploadFile) -> dict[str, object]:
    filename = file.filename or "upload.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "当前仅支持 .md、.markdown 和 .txt 文档")

    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if not content:
        raise HTTPException(422, "上传文件不能为空")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "单个文档不能超过 5 MiB")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "当前仅支持 UTF-8 编码文本") from exc
    if not text.strip():
        raise HTTPException(422, "文档不能只包含空白字符")

    document_id = str(uuid4())
    document_dir = data_directory() / document_id
    document_dir.mkdir(parents=True, exist_ok=False)
    (document_dir / f"source{suffix}").write_bytes(content)
    (document_dir / "content.txt").write_text(text, encoding="utf-8")
    metadata = {
        "document_id": document_id,
        "original_filename": filename,
        "content_type": file.content_type,
        "byte_size": len(content),
        "character_count": len(text),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": f"{document_id}/source{suffix}",
        "text_path": f"{document_id}/content.txt",
    }
    (document_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata
