import os
import json
import base64
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ml_backend.schemas.document import (
    DocumentExtractionRequest,
    DocumentExtractionResponse
)
from ml_backend.schemas.medical_fact import NormalizedTerm
from ml_backend.services.vision_extract import vision_extraction_service, DocumentExtractionError
from ml_backend.services.normalization import normalization_service
from ml_backend.utils.multipart import parse_raw_multipart, validate_uploaded_document

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Perception & Normalization"])


class NormalizationBatchRequest(BaseModel):
    terms: List[str] = Field(..., description="List of raw medical terms to normalize")


class NormalizationBatchResponse(BaseModel):
    results: Dict[str, NormalizedTerm] = Field(..., description="Dictionary mapping raw term to normalized concept")


@router.post("/documents/extract", response_model=DocumentExtractionResponse)
async def extract_document(request: Request):
    """
    Extract structured medical facts, classifications, and lab results from an uploaded medical document (image or PDF).
    Supports:
    1. Standard JSON payload with Base64 encoded file
    2. JSON payload referencing an existing server file_path
    3. Frontend multipart/form-data upload (FormData with 'file', 'document_id', etc.)
    4. Direct binary stream upload

    Strictly validates upload content and rejects fake or empty payloads.
    """
    content_type = request.headers.get("content-type", "").lower()
    raw_body = await request.body()

    doc_id = None
    p_id = "P_DEMO_001"
    image_bytes = b""
    mime_type = "image/jpeg"

    if "application/json" in content_type and raw_body:
        try:
            body_dict = json.loads(raw_body.decode("utf-8"))
            req_model = DocumentExtractionRequest.model_validate(body_dict)
            doc_id = req_model.document_id
            p_id = req_model.patient_id or "P_DEMO_001"
            mime_type = req_model.mime_type or "image/jpeg"

            if req_model.image_base64:
                try:
                    image_bytes = base64.b64decode(req_model.image_base64)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid base64 encoded image string."
                    )
            elif req_model.file_path:
                if not os.path.exists(req_model.file_path):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Specified document file_path '{req_model.file_path}' does not exist on server."
                    )
                with open(req_model.file_path, "rb") as f:
                    image_bytes = f.read()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed JSON payload: {str(e)}"
            )
    elif "multipart/form-data" in content_type:
        extracted_bytes, extracted_mime, form_fields = parse_raw_multipart(content_type, raw_body)
        if extracted_bytes:
            image_bytes = extracted_bytes
            mime_type = extracted_mime
        if "document_id" in form_fields:
            doc_id = form_fields["document_id"]
        if "patient_id" in form_fields:
            p_id = form_fields["patient_id"]
    elif raw_body:
        image_bytes = raw_body
        mime_type = content_type or "image/jpeg"

    # Strict Validation: Non-empty, allowed formats, rejects dummy bytes (P0 fix)
    validated_mime = validate_uploaded_document(image_bytes=image_bytes, mime_type=mime_type)

    if not doc_id:
        doc_id = f"DOC_{int(os.times().elapsed * 1000)}"

    try:
        response = vision_extraction_service.extract_document(
            image_bytes=image_bytes,
            mime_type=validated_mime,
            document_id=doc_id,
            patient_id=p_id
        )
    except DocumentExtractionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected extraction failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal extraction error: {str(e)}"
        )

    if not response.success:
        err_msg = response.errors[0] if response.errors else "Failed to extract medical document."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)

    return response


@router.post("/documents/normalize", response_model=NormalizationBatchResponse)
def normalize_batch(batch: NormalizationBatchRequest):
    """
    Batch normalize a list of colloquial, regional, or abbreviated medical terms into standardized clinical concepts.
    """
    normalized_results: Dict[str, NormalizedTerm] = {}
    for term in batch.terms:
        norm = normalization_service.normalize_term(term)
        normalized_results[term] = norm
    return NormalizationBatchResponse(results=normalized_results)
