#!/usr/bin/env python3
"""
MediKiosk AI/ML Service Test CLI
Run individual document perception tests or execute the complete end-to-end hackathon demo scenario.

Usage:
  python test_document.py --file ml_backend/sample_documents/prescription_01.jpg
  python test_document.py --file ml_backend/sample_documents/lab_report_01.jpg
  python test_document.py --demo
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml_backend.config import settings
from ml_backend.services.vision_extract import vision_extraction_service
from ml_backend.services.normalization import normalization_service
from ml_backend.services.lab_validator import lab_validator_service
from ml_backend.services.timeline import timeline_service
from ml_backend.services.conflict_detector import conflict_detector_service
from ml_backend.services.snapshot_generator import snapshot_generator_service
from ml_backend.services.doctor_qa import doctor_qa_service
from ml_backend.schemas.snapshot import CurrentIntakeHistory, SnapshotRequest
from ml_backend.schemas.qa import DoctorQARequest


def print_banner(title: str):
    width = 70
    print("\n" + "=" * width)
    print(f" {title.center(width - 2)}")
    print("=" * width)


def test_single_file(file_path: str, provider: str = "mock"):
    path = Path(file_path)
    if not path.exists():
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    print_banner(f"TESTING DOCUMENT: {path.name}")
    print(f"Provider: {provider}")

    with open(path, "rb") as f:
        image_bytes = f.read()

    doc_id = f"DOC_{path.stem.upper()}"
    mime = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "application/pdf"

    res = vision_extraction_service.extract_document(
        image_bytes=image_bytes,
        mime_type=mime,
        document_id=doc_id,
        provider=provider
    )

    print(f"\n[+] Extraction Status: {'SUCCESS' if res.success else 'FAILED'}")
    print(f"[+] Document ID: {res.document_id}")
    print(f"[+] Document Type: {res.document_type.value} (Confidence: {res.confidence:.2f})")
    print(f"[+] Document Date: {res.extraction.document_date}")
    print(f"[+] Hospital/Clinic: {res.extraction.hospital_name}")
    print(f"[+] Doctor: {res.extraction.doctor_name}")

    if res.extraction.diagnoses:
        print("\n--- Diagnoses ---")
        for d in res.extraction.diagnoses:
            print(f"  • {d.condition} [Status: {d.status or 'N/A'}] (Source: {d.source.document_id if d.source else doc_id})")

    if res.extraction.medications:
        print("\n--- Medications ---")
        for m in res.extraction.medications:
            print(f"  • {m.name} | Dose: {m.dosage or 'N/A'} | Freq: {m.frequency or 'N/A'} | Route: {m.route or 'N/A'}")

    if res.extraction.lab_results:
        print("\n--- Lab Results (Deterministic Validation) ---")
        for l in res.extraction.lab_results:
            flag = "[ABNORMAL]" if l.abnormal is True else ("[NORMAL]" if l.abnormal is False else "[INDETERMINATE]")
            print(f"  • {l.test_name}: {l.value} {l.unit or ''} (Ref: {l.reference_range or 'N/A'}) -> {flag} ({l.interpretation})")

    if res.extraction.allergies:
        print("\n--- Allergies ---")
        for a in res.extraction.allergies:
            print(f"  • {a.substance} (Reaction: {a.reaction or 'Not specified'})")

    print("\n--- Normalized Facts Generated ---")
    for f in res.normalized_facts:
        print(f"  [{f.type.value.upper()}] Raw: '{f.raw_value}' -> Normalized: '{f.normalized_value}' (Doc: {f.source_document_id})")

    print("\n" + "-" * 70)


def run_full_demo(provider: str = "mock"):
    print_banner("MEDIKIOSK AI/ML CLINICAL SYNTHESIS PIPELINE DEMO")
    print("Simulating OPD intake scenario from Section 26 of Hackathon Specification...\n")

    # Step 1: Ingest 3 Historical Documents
    docs_to_process = [
        ("prescription_01.jpg", "DOC_001", "Prescription"),
        ("lab_report_01.jpg", "DOC_002", "Lab Report"),
        ("discharge_summary_01.jpg", "DOC_003", "Discharge Summary")
    ]

    extracted_docs = []
    all_facts = []
    all_labs = []

    print_banner("PHASE 1: DOCUMENT EXTRACTION & NORMALIZATION")
    for filename, doc_id, label in docs_to_process:
        file_path = settings.SAMPLE_DOCS_DIR / filename
        with open(file_path, "rb") as f:
            image_bytes = f.read()

        print(f"\n[*] Processing {label} ({doc_id}) via Vision LLM...")
        res = vision_extraction_service.extract_document(
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            document_id=doc_id,
            provider=provider
        )
        extracted_docs.append(res.extraction)
        all_facts.extend(res.normalized_facts)
        all_labs.extend(res.extraction.lab_results)
        print(f"    Type: {res.document_type.value} | Date: {res.extraction.document_date}")
        print(f"    Extracted: {len(res.extraction.diagnoses)} diagnoses, {len(res.extraction.medications)} meds, {len(res.extraction.lab_results)} labs, {len(res.extraction.allergies)} allergies")

    # Step 2: Chronological Timeline
    print_banner("PHASE 2: CHRONOLOGICAL TIMELINE ENGINE")
    timeline_res = timeline_service.build_chronological_timeline(extracted_docs)
    print(f"Aggregated {timeline_res.total_events} chronological events:")
    for ev in timeline_res.events:
        date_str = ev.event_date or "Undated"
        print(f"  [{date_str}] ({ev.event_type.value.upper()}) {ev.summary} (Source: {ev.source_document_id})")

    # Step 3: Current Clinical Intake + Conflict Detection
    print_banner("PHASE 3: CURRENT INTAKE & CONFLICT DETECTION")
    current_history = CurrentIntakeHistory(
        chief_complaint="Fever and cough",
        duration="3 days",
        symptoms=["fever", "cough"],
        allergies=["No known allergies", "NKDA"],
        past_history=["None reported by patient"]
    )
    print(f"Current Intake Complaint: '{current_history.chief_complaint}' ({current_history.duration})")
    print(f"Current Intake Allergy statement: {current_history.allergies}")

    alerts = conflict_detector_service.detect_conflicts(
        current_history=current_history,
        extracted_documents=extracted_docs,
        patient_facts=all_facts
    )

    print(f"\nDetected {len(alerts)} Clinical Inconsistencies / Alerts:")
    for alert in alerts:
        print(f"  [ALERT - {alert.severity.upper()}] ({alert.type}): {alert.message}")
        print(f"    Source Documents: {alert.source_document_ids}")

    # Step 4: Physician Snapshot Synthesis
    print_banner("PHASE 4: PHYSICIAN SNAPSHOT SYNTHESIS")
    snapshot_req = SnapshotRequest(
        patient_id="P_DEMO_001",
        current_history=current_history,
        facts=all_facts,
        timeline=timeline_res.events,
        documents=extracted_docs,
        lab_results=all_labs
    )
    snapshot = snapshot_generator_service.generate_snapshot(snapshot_req, provider=provider)

    print(f"Chief Complaint: {snapshot.chief_complaint}")
    print(f"HPI: {snapshot.hpi}")
    print("\nPast Medical History:")
    for pmh in snapshot.past_medical_history:
        print(f"  • {pmh.get('condition')} (Raw: '{pmh.get('raw_term')}') [Source: {pmh.get('source_document_ids')}]")

    print("\nMedications:")
    for med in snapshot.medications:
        print(f"  • {med.get('name')} {med.get('dosage') or ''} - {med.get('frequency') or ''} [Source: {med.get('source_document_ids')}]")

    print("\nAllergies (Highlighted):")
    for al in snapshot.allergies:
        print(f"  • {al.get('substance')} (Reaction: {al.get('reaction')}) [Source: {al.get('source_document_ids')}]")

    print("\nKey Abnormal Investigations:")
    for lab in snapshot.previous_investigations:
        if lab.get("abnormal"):
            print(f"  • {lab.get('test_name')}: {lab.get('value')} {lab.get('unit')} (Ref: {lab.get('reference_range')}) [Source: {lab.get('source_document_ids')}]")

    # Step 5: Doctor Q&A
    print_banner("PHASE 5: DOCTOR Q&A INQUIRIES & CITATIONS")
    queries = [
        "What happened during the last visit?",
        "Show me the diabetes history.",
        "Why was the medication changed?",
        "Has the patient been hospitalized?",
        "What allergies are documented?"
    ]

    for q in queries:
        qa_req = DoctorQARequest(
            patient_id="P_DEMO_001",
            question=q,
            context_facts=all_facts,
            context_timeline=timeline_res.events,
            context_documents=extracted_docs,
            current_history=current_history
        )
        qa_res = doctor_qa_service.answer_question(qa_req, provider=provider)
        print(f"\nQ: {qa_res.question}")
        print(f"A: {qa_res.answer}")
        citations = [f"{s.document_id} ({s.document_type or 'doc'})" for s in qa_res.source_references]
        print(f"   Sources Cited: {citations}")

    print_banner("DEMO COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MediKiosk ML Backend CLI")
    parser.add_argument("--file", type=str, help="Path to document image/PDF to test extraction")
    parser.add_argument("--demo", action="store_true", help="Run full hackathon demo scenario")
    parser.add_argument("--provider", type=str, default="mock", help="LLM Provider: gemini, openai, or mock")

    args = parser.parse_args()

    if args.demo:
        run_full_demo(provider=args.provider)
    elif args.file:
        test_single_file(args.file, provider=args.provider)
    else:
        # Default to running demo
        run_full_demo(provider=args.provider)
