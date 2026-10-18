"""
Temporary in-process document and SHA-256 registry for Milestone 0.

Replaced by PostgreSQL with uniqueness constraints in Milestone 2.
Not safe across multiple processes or container restarts.
"""

from __future__ import annotations

from threading import Lock
from uuid import UUID

from app.schemas.documents import DocumentRecord


class DocumentRegistry:
    """Thread-safe in-memory store keyed by document id and content hash."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, DocumentRecord] = {}
        self._by_hash: dict[str, UUID] = {}
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._by_hash.clear()

    def get_by_id(self, document_id: UUID) -> DocumentRecord | None:
        with self._lock:
            return self._by_id.get(document_id)

    def get_by_hash(self, sha256: str) -> DocumentRecord | None:
        with self._lock:
            document_id = self._by_hash.get(sha256)
            if document_id is None:
                return None
            return self._by_id.get(document_id)

    def list_documents(self) -> list[DocumentRecord]:
        with self._lock:
            return sorted(self._by_id.values(), key=lambda d: d.uploaded_at, reverse=True)

    def register(self, record: DocumentRecord) -> DocumentRecord:
        """
        Register a new document.

        Raises ValueError if the SHA-256 is already registered (exact-file duplicate).
        Callers should check get_by_hash first for a friendly duplicate response.
        """
        with self._lock:
            existing_id = self._by_hash.get(record.sha256)
            if existing_id is not None:
                raise ValueError(f"Document with sha256={record.sha256} already exists")
            if record.id in self._by_id:
                raise ValueError(f"Document id={record.id} already exists")
            self._by_id[record.id] = record
            self._by_hash[record.sha256] = record.id
            return record

    def update(self, record: DocumentRecord) -> DocumentRecord:
        with self._lock:
            if record.id not in self._by_id:
                raise KeyError(f"Unknown document id={record.id}")
            existing = self._by_id[record.id]
            if existing.sha256 != record.sha256:
                raise ValueError("SHA-256 of an existing document cannot change")
            self._by_id[record.id] = record
            return record


_registry = DocumentRegistry()


def get_registry() -> DocumentRegistry:
    return _registry
