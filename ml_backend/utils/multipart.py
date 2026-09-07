import os
import re
import email
import logging
from typing import Tuple, Dict, Any, Optional, Set
from fastapi import HTTPException, status
from ml_backend.config import settings

logger = logging.getLogger(__name__)


def parse_raw_multipart(content_type_header: str, body: bytes) -> Tuple[bytes, str, Dict[str, str]]:
    """
    Parse multipart/form-data payloads natively using standard Python libraries.
    Extracts the file binary bytes, detected MIME type, and text form fields.
    """
    image_bytes = b""
    mime_type = "image/jpeg"
    fields: Dict[str, str] = {}

    if not body or not content_type_header:
        return image_bytes, mime_type, fields

    try:
        header_bytes = f"Content-Type: {content_type_header}\r\n\r\n".encode("latin-1")
        msg = email.message_from_bytes(header_bytes + body)
        for part in msg.walk():
            cd = part.get("Content-Disposition", "")
            if 'filename="' in cd or "filename*=" in cd:
                image_bytes = part.get_payload(decode=True) or b""
                mime_type = part.get_content_type()
            elif 'name="' in cd:
                name_m = re.search(r'name="([^"]+)"', cd)
                if name_m:
                    field_name = name_m.group(1)
                    val = part.get_payload(decode=True) or b""
                    fields[field_name] = val.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        logger.warning(f"Error parsing raw multipart data: {e}")

    return image_bytes, mime_type, fields


def validate_uploaded_document(
    image_bytes: bytes,
    mime_type: Optional[str] = None,
    allowed_types: Optional[Set[str]] = None,
    max_size_bytes: Optional[int] = None
) -> str:
    """
    Strict validation for uploaded medical documents:
    1. Ensures payload is non-empty.
    2. Explicitly rejects fake/dummy document placeholders.
    3. Enforces maximum size bounds.
    4. Enforces valid MIME types (JPEG, PNG, WebP, TIFF, HEIC, PDF).
    """
    allowed_mimes = allowed_types or settings.ALLOWED_MIME_TYPES
    max_size = max_size_bytes or settings.MAX_UPLOAD_SIZE_BYTES

    # 1. Non-empty check
    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document image provided. A valid non-empty image (JPEG, PNG, WebP, TIFF) or PDF file is required."
        )

    # 2. Reject fake / placeholder documents (P0 Fix)
    if image_bytes == b"DUMMY_IMAGE_BYTES" or image_bytes.strip() == b"DUMMY_IMAGE_BYTES":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dummy placeholder bytes are rejected. A real medical document image or PDF must be uploaded."
        )

    # 3. Size check
    if len(image_bytes) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded document exceeds maximum allowed size of {max_mb} MB."
        )

    # 4. MIME type check
    clean_mime = (mime_type or "image/jpeg").lower().split(";")[0].strip()
    if clean_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type '{clean_mime}'. Allowed formats: JPEG, PNG, WebP, TIFF, HEIC, PDF."
        )

    return clean_mime
