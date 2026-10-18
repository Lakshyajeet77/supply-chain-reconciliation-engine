"""Content hashing for exact-file duplicate detection."""

import hashlib


def sha256_hex(data: bytes) -> str:
    """Return lowercase hex SHA-256 of the original file bytes."""
    return hashlib.sha256(data).hexdigest()
