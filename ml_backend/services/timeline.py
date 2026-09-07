import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from ml_backend.schemas.timeline import TimelineEvent, TimelineEventType, TimelineResponse
from ml_backend.schemas.document import ExtractedDocument, DocumentTypeEnum

logger = logging.getLogger(__name__)


def parse_sortable_date(date_str: Optional[str]) -> str:
    """
    Returns a sortable string representation of a date.
    Empty/None returns '9999-99-99' so undated events appear after dated events.
    """
    if not date_str or not date_str.strip():
        return "9999-99-99"
    cleaned = date_str.strip()
    # If 4 digit year only (e.g. '2019')
    if re.match(r"^\d{4}$", cleaned):
        return f"{cleaned}-01-01"
    # If YYYY-MM format
    if re.match(r"^\d{4}-\d{2}$", cleaned):
        return f"{cleaned}-01"
    # If already ISO YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        return cleaned
    return cleaned


class TimelineService:
    def extract_events_from_document(self, doc: ExtractedDocument) -> List[TimelineEvent]:
        """
        Generate timeline events from a single ExtractedDocument.
        """
        events: List[TimelineEvent] = []
        doc_date = doc.document_date
        doc_id = doc.document_id
        doc_type_val = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)

        # 1. Hospitalization / Consultation event from document metadata
        if doc.document_type == DocumentTypeEnum.DISCHARGE_SUMMARY:
            events.append(
                TimelineEvent(
                    event_date=doc_date,
                    event_type=TimelineEventType.HOSPITALIZATION,
                    summary=f"Hospitalization & Discharge at {doc.hospital_name or 'Hospital'}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"hospital": doc.hospital_name, "doctor": doc.doctor_name}
                )
            )
        elif doc.document_type == DocumentTypeEnum.PRESCRIPTION:
            events.append(
                TimelineEvent(
                    event_date=doc_date,
                    event_type=TimelineEventType.CONSULTATION,
                    summary=f"Outpatient Consultation with {doc.doctor_name or 'Physician'} ({doc.hospital_name or 'Clinic'})",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"doctor": doc.doctor_name, "clinic": doc.hospital_name}
                )
            )

        # 2. Diagnoses
        for diag in doc.diagnoses:
            events.append(
                TimelineEvent(
                    event_date=doc_date,
                    event_type=TimelineEventType.DIAGNOSIS,
                    summary=f"Diagnosis documented: {diag.condition}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"raw_text": diag.raw_text, "status": diag.status, "code": diag.code}
                )
            )

        # 3. Medications prescribed/administered
        for med in doc.medications:
            dosage_str = f" ({med.dosage})" if med.dosage else ""
            freq_str = f" {med.frequency}" if med.frequency else ""
            events.append(
                TimelineEvent(
                    event_date=doc_date,
                    event_type=TimelineEventType.MEDICATION,
                    summary=f"Medication recorded: {med.name}{dosage_str}{freq_str}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration,
                        "route": med.route
                    }
                )
            )

        # 4. Lab Results / Investigations
        for lab in doc.lab_results:
            abn_str = " (Abnormal)" if lab.abnormal is True else (" (Normal)" if lab.abnormal is False else "")
            unit_str = f" {lab.unit}" if lab.unit else ""
            val_str = f": {lab.value}{unit_str}" if lab.value is not None else ""
            events.append(
                TimelineEvent(
                    event_date=doc_date,
                    event_type=TimelineEventType.INVESTIGATION,
                    summary=f"Lab test: {lab.test_name}{val_str}{abn_str}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={
                        "test_name": lab.test_name,
                        "value": lab.value,
                        "unit": lab.unit,
                        "reference_range": lab.reference_range,
                        "abnormal": lab.abnormal
                    }
                )
            )

        # 5. Procedures and Surgeries
        for proc in doc.procedures:
            events.append(
                TimelineEvent(
                    event_date=proc.date or doc_date,
                    event_type=TimelineEventType.PROCEDURE,
                    summary=f"Procedure: {proc.name}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"indication": proc.indication}
                )
            )

        for surg in doc.surgeries:
            events.append(
                TimelineEvent(
                    event_date=surg.date or doc_date,
                    event_type=TimelineEventType.SURGERY,
                    summary=f"Surgery: {surg.name}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"indication": surg.indication}
                )
            )

        # 6. Follow-up
        for fu in doc.follow_up:
            events.append(
                TimelineEvent(
                    event_date=fu.date or doc_date,
                    event_type=TimelineEventType.FOLLOW_UP,
                    summary=f"Follow-up advised: {fu.instructions}",
                    source_document_id=doc_id,
                    source_document_type=doc_type_val,
                    details={"doctor_or_dept": fu.doctor_or_dept}
                )
            )

        return events

    def build_chronological_timeline(
        self,
        documents: List[ExtractedDocument],
        additional_events: Optional[List[TimelineEvent]] = None,
        ascending: bool = True
    ) -> TimelineResponse:
        """
        Build an aggregated, chronologically sorted timeline across multiple documents.
        Never invents missing dates. Undated events (event_date=None) are placed safely at the end.
        """
        all_events: List[TimelineEvent] = []

        for doc in documents:
            doc_events = self.extract_events_from_document(doc)
            all_events.extend(doc_events)

        if additional_events:
            all_events.extend(additional_events)

        # Sort: dated items sorted by parse_sortable_date, undated items at end
        def sort_key(e: TimelineEvent) -> Tuple[int, str]:
            if e.event_date:
                return (0, parse_sortable_date(e.event_date))
            else:
                return (1, "9999-99-99")

        sorted_events = sorted(all_events, key=sort_key, reverse=not ascending)

        return TimelineResponse(
            patient_id=documents[0].patient_name if documents else None,
            total_events=len(sorted_events),
            events=sorted_events
        )


timeline_service = TimelineService()
