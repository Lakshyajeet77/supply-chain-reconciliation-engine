"""Filesystem storage for uploaded documents (outside public frontend assets)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID


class FileStorage:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def build_path(self, document_id: UUID, extension: str) -> Path:
        safe_ext = extension if extension.startswith(".") else f".{extension}"
        return self.upload_dir / f"{document_id}{safe_ext}"

    def save(self, document_id: UUID, extension: str, data: bytes) -> Path:
        path = self.build_path(document_id, extension)
        path.write_bytes(data)
        return path
