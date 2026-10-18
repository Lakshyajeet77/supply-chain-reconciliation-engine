"""
Pure-Python file validation using magic-byte signatures and light decode checks.

Do not trust filename or client-supplied MIME type alone.
"""

from __future__ import annotations

from dataclasses import dataclass

# Signatures
_PDF_MAGIC = b"%PDF-"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8\xff"

class InvalidUploadError(ValueError):
    """Raised when an upload fails validation. Safe to surface to API clients."""


@dataclass(frozen=True)
class ValidatedFile:
    content_type: str
    extension: str
    kind: str
    size_bytes: int


def _detect_kind(data: bytes) -> str | None:
    if data.startswith(_PDF_MAGIC):
        return "pdf"
    if data.startswith(_PNG_MAGIC):
        return "png"
    if data.startswith(_JPEG_SOI):
        return "jpeg"
    return None


def _validate_pdf_structure(data: bytes) -> None:
    # Minimal structure checks: header already matched; require EOF marker.
    if b"%%EOF" not in data[-2048:]:
        # Some valid PDFs pad after EOF; also check whole file once.
        if b"%%EOF" not in data:
            raise InvalidUploadError("PDF appears corrupted or incomplete (missing %%EOF).")


def _validate_png_structure(data: bytes) -> None:
    # PNG: 8-byte signature + at least one IHDR chunk (length 13, type IHDR).
    if len(data) < 33:
        raise InvalidUploadError("PNG file is too small to be valid.")
    # Bytes 12:16 of file (after signature + length) should be IHDR for a normal PNG.
    if data[12:16] != b"IHDR":
        raise InvalidUploadError("PNG file is missing IHDR chunk.")
    if b"IEND" not in data:
        raise InvalidUploadError("PNG appears corrupted or incomplete (missing IEND).")


def _validate_jpeg_structure(data: bytes) -> None:
    if len(data) < 4:
        raise InvalidUploadError("JPEG file is too small to be valid.")
    # EOI marker 0xFFD9 should appear near the end for a complete image.
    if not data.rstrip(b"\x00").endswith(b"\xff\xd9"):
        # Allow trailing bytes after EOI in some exporters; require EOI somewhere near end.
        if b"\xff\xd9" not in data[-64:]:
            raise InvalidUploadError("JPEG appears corrupted or incomplete (missing EOI).")


def validate_upload(data: bytes, max_upload_bytes: int, declared_filename: str | None = None) -> ValidatedFile:
    if not data:
        raise InvalidUploadError("Empty files are not allowed.")
    if len(data) > max_upload_bytes:
        raise InvalidUploadError(
            f"File exceeds maximum size of {max_upload_bytes} bytes."
        )

    kind = _detect_kind(data)
    if kind is None:
        raise InvalidUploadError(
            "Unsupported or unrecognized file type. Allowed: PDF, PNG, JPEG."
        )

    if kind == "pdf":
        _validate_pdf_structure(data)
        content_type, extension = "application/pdf", ".pdf"
    elif kind == "png":
        _validate_png_structure(data)
        content_type, extension = "image/png", ".png"
    else:
        _validate_jpeg_structure(data)
        content_type, extension = "image/jpeg", ".jpg"

    # Optional soft check: extension mismatch is noted but signature wins.
    if declared_filename:
        lower = declared_filename.lower()
        expected_exts = {
            "pdf": (".pdf",),
            "png": (".png",),
            "jpeg": (".jpg", ".jpeg"),
        }[kind]
        if not any(lower.endswith(ext) for ext in expected_exts):
            # Reject rather than silently trust a misleading name.
            raise InvalidUploadError(
                f"Filename extension does not match detected file type ({kind})."
            )

    return ValidatedFile(
        content_type=content_type,
        extension=extension,
        kind=kind,
        size_bytes=len(data),
    )
