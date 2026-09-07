import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.schemas import Patient, Document, LabResult
from app.models.pydantic_models import DocumentExtractResponse
from app.ai.vision_pipeline import extract_and_normalize

router = APIRouter(prefix="/api/documents", tags=["Medical Document Digitization & OCR"])

UPLOAD_DIR = "./data/sample_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentExtractResponse, status_code=status.HTTP_201_CREATED)
async def upload_medical_document(
    patient_id: str = Form(...),
    document_type: str = Form("lab_report"),  # prescription, lab_report, discharge_summary
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    file_ext = os.path.splitext(file.filename)[1]
    doc_uuid = str(uuid.uuid4())
    saved_filename = f"{patient_id}_{doc_uuid[:8]}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    # Save uploaded file
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Run Vision Intelligence Pipeline (document perception, terminology
    # normalization, deterministic lab range validation)
    document_id = f"DOC-{doc_uuid[:8].upper()}"
    extracted = extract_and_normalize(
        file_path,
        document_type=document_type,
        patient_id=patient_id,
        document_id=document_id,
    )
    ocr_text = extracted["ocr_text"]

    # Store document record in DB
    db_doc = Document(
        document_id=document_id,
        patient_id=patient_id,
        file_name=file.filename,
        file_path=file_path,
        document_type=document_type,
        document_date=extracted["extracted_date"],
        ocr_text=ocr_text
    )
    db.add(db_doc)
    db.flush()

    # Store extracted lab results in DB
    for lab in extracted["lab_results"]:
        lab_db = LabResult(
            result_id=f"LAB-{uuid.uuid4().hex[:8].upper()}",
            document_id=db_doc.document_id,
            patient_id=patient_id,
            test_name=lab["test_name"],
            value=str(lab["value"]),
            unit=lab.get("unit"),
            reference_range=lab.get("reference_range"),
            abnormal=lab.get("abnormal", False),
            category=lab.get("category", "General")
        )
        db.add(lab_db)

    db.commit()

    return {
        "document_id": db_doc.document_id,
        "patient_id": patient_id,
        "document_type": document_type,
        "document_date": db_doc.document_date,
        "ocr_text": ocr_text,
        "extracted_diagnoses": extracted["diagnoses"],
        "extracted_medications": extracted["medications"],
        "lab_results": extracted["lab_results"]
    }


@router.get("/patient/{patient_id}")
def get_patient_documents(patient_id: str, db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.patient_id == patient_id).all()
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    return {
        "patient_id": patient_id,
        "documents_count": len(docs),
        "documents": [
            {
                "document_id": d.document_id,
                "file_name": d.file_name,
                "document_type": d.document_type,
                "document_date": d.document_date,
                "created_at": d.created_at
            } for d in docs
        ],
        "lab_timeline": [
            {
                "result_id": l.result_id,
                "test_name": l.test_name,
                "value": l.value,
                "unit": l.unit,
                "reference_range": l.reference_range,
                "abnormal": l.abnormal
            } for l in labs
        ]
    }
