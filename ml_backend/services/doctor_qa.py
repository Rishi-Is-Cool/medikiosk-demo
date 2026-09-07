import json
import logging
from typing import Optional, Dict, Any, List
from ml_backend.config import settings
from ml_backend.schemas.qa import (
    DoctorQARequest,
    DoctorQAResponse,
    QueryPatternEnum,
    SourceReference
)
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum
from ml_backend.schemas.timeline import TimelineEvent
from ml_backend.schemas.document import ExtractedDocument
from ml_backend.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class DoctorQAService:
    def __init__(self, prompt_path: Optional[str] = None):
        self.prompt_path = prompt_path or str(settings.PROMPTS_DIR / "doctor_qa.txt")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load prompt from {self.prompt_path}: {e}")
            return "Answer the doctor query from the retrieved patient records with source references."

    def classify_query(self, question: str) -> QueryPatternEnum:
        """Categorize the clinical query pattern."""
        q = question.lower()
        if "last visit" in q or "previous visit" in q or "recent visit" in q or "last encounter" in q:
            return QueryPatternEnum.LAST_VISIT
        elif "diabet" in q or "sugar" in q or "hba1c" in q or "glyc" in q:
            return QueryPatternEnum.DIABETES_HISTORY
        elif "medication" in q or "drug" in q or "dose" in q or "prescri" in q or "changed" in q:
            return QueryPatternEnum.MEDICATION_CHANGE
        elif "hospital" in q or "admit" in q or "discharge" in q or "ward" in q or "surgery" in q:
            return QueryPatternEnum.HOSPITALIZATION
        elif "allerg" in q or "reaction" in q or "sensitivity" in q or "contraindicat" in q:
            return QueryPatternEnum.ALLERGIES
        return QueryPatternEnum.GENERAL

    def retrieve_relevant_records(
        self,
        pattern: QueryPatternEnum,
        facts: List[PatientFact],
        timeline: List[TimelineEvent],
        documents: List[ExtractedDocument]
    ) -> List[Dict[str, Any]]:
        """
        Structured record retrieval filter based on pattern classification.
        """
        retrieved: List[Dict[str, Any]] = []

        if pattern == QueryPatternEnum.LAST_VISIT:
            # Sort documents by date descending and get latest
            dated_docs = [d for d in documents if d.document_date]
            if dated_docs:
                sorted_docs = sorted(dated_docs, key=lambda d: d.document_date or "", reverse=True)
                latest = sorted_docs[0]
                retrieved.append({
                    "type": "latest_document",
                    "document_id": latest.document_id,
                    "document_type": latest.document_type.value,
                    "date": latest.document_date,
                    "summary": f"{latest.document_type.value} from {latest.hospital_name or 'Clinic'}",
                    "diagnoses": [d.condition for d in latest.diagnoses],
                    "medications": [m.name for m in latest.medications],
                    "labs": [f"{l.test_name}: {l.value} {l.unit or ''}" for l in latest.lab_results]
                })

        elif pattern == QueryPatternEnum.DIABETES_HISTORY:
            # Retrieve diabetes facts, diabetes meds (Metformin, Glimepiride, Insulin), and HbA1c/FBS labs
            for f in facts:
                val_lower = (f.normalized_value or f.raw_value).lower()
                if "diabet" in val_lower or "sugar" in val_lower or "metformin" in val_lower or "glimepiride" in val_lower:
                    retrieved.append(f.model_dump())
            for doc in documents:
                for lab in doc.lab_results:
                    if lab.test_name.lower() in ["hba1c", "fasting blood sugar", "fbs", "ppbs", "random blood sugar", "rbs", "glucose"]:
                        retrieved.append({
                            "type": "lab_finding",
                            "document_id": doc.document_id,
                            "date": doc.document_date,
                            "test": lab.test_name,
                            "value": lab.value,
                            "unit": lab.unit,
                            "reference_range": lab.reference_range,
                            "abnormal": lab.abnormal
                        })

        elif pattern == QueryPatternEnum.MEDICATION_CHANGE:
            for f in facts:
                if f.type == FactTypeEnum.MEDICATION:
                    retrieved.append(f.model_dump())
            for ev in timeline:
                if ev.event_type.value in ["medication", "discharge", "consultation"]:
                    retrieved.append(ev.model_dump())

        elif pattern == QueryPatternEnum.HOSPITALIZATION:
            for doc in documents:
                if doc.document_type.value in ["discharge_summary", "hospitalization"]:
                    retrieved.append({
                        "document_id": doc.document_id,
                        "hospital": doc.hospital_name,
                        "date": doc.document_date,
                        "diagnoses": [d.condition for d in doc.diagnoses],
                        "procedures": [p.name for p in doc.procedures],
                        "notes": doc.clinical_notes
                    })
            for ev in timeline:
                if ev.event_type.value in ["hospitalization", "surgery", "discharge"]:
                    retrieved.append(ev.model_dump())

        elif pattern == QueryPatternEnum.ALLERGIES:
            for f in facts:
                if f.type == FactTypeEnum.ALLERGY:
                    retrieved.append(f.model_dump())
            for doc in documents:
                for a in doc.allergies:
                    retrieved.append({
                        "document_id": doc.document_id,
                        "substance": a.substance,
                        "reaction": a.reaction,
                        "severity": a.severity
                    })

        else:
            # General search across all facts and events
            for f in facts:
                retrieved.append(f.model_dump())
            for ev in timeline:
                retrieved.append(ev.model_dump())

        return retrieved

    def answer_question(
        self,
        request: DoctorQARequest,
        provider: Optional[str] = None
    ) -> DoctorQAResponse:
        """
        Synthesizes an evidence-backed answer to a doctor's question with precise source citations.
        """
        pattern = request.query_type or self.classify_query(request.question)
        retrieved_evidence = self.retrieve_relevant_records(
            pattern=pattern,
            facts=request.context_facts,
            timeline=request.context_timeline,
            documents=request.context_documents
        )

        if not retrieved_evidence and not request.context_documents and not request.context_facts:
            return DoctorQAResponse(
                question=request.question,
                interpreted_pattern=pattern,
                answer="No documentation found in the available patient records.",
                source_references=[],
                retrieved_evidence=[],
                data_available=False,
                confidence=1.0
            )

        payload = {
            "question": request.question,
            "interpreted_pattern": pattern.value,
            "retrieved_evidence": retrieved_evidence,
            "current_history": request.current_history.model_dump() if request.current_history else None
        }

        llm_client = get_llm_client(provider)
        try:
            raw_res = llm_client.generate_text_synthesis(
                system_prompt=self.prompt_template,
                user_content=json.dumps(payload, indent=2, default=str)
            )
            response = DoctorQAResponse.model_validate(raw_res)
            response.retrieved_evidence = retrieved_evidence
            return response
        except Exception as e:
            logger.warning(f"Doctor QA synthesis failed: {e}. Generating fallback answer.", exc_info=True)
            return self._build_deterministic_qa_fallback(request.question, pattern, retrieved_evidence)

    def _build_deterministic_qa_fallback(
        self,
        question: str,
        pattern: QueryPatternEnum,
        evidence: List[Dict[str, Any]]
    ) -> DoctorQAResponse:
        """Deterministic QA fallback when LLM is offline or error occurs."""
        sources: List[SourceReference] = []
        doc_ids = set()

        for item in evidence:
            doc_id = item.get("source_document_id") or item.get("document_id")
            if doc_id and doc_id not in doc_ids:
                doc_ids.add(doc_id)
                sources.append(
                    SourceReference(
                        document_id=doc_id,
                        document_type=item.get("document_type"),
                        date=item.get("date_recorded") or item.get("date"),
                        excerpt=item.get("normalized_value") or item.get("summary") or str(item)
                    )
                )

        if not evidence:
            return DoctorQAResponse(
                question=question,
                interpreted_pattern=pattern,
                answer="No documentation found in the available patient records.",
                source_references=[],
                retrieved_evidence=[],
                data_available=False,
                confidence=1.0
            )

        answer = f"Based on retrieved patient records ({', '.join(sorted(doc_ids))}), relevant documented entries include: "
        summaries = []
        for item in evidence[:5]:
            if "normalized_value" in item:
                summaries.append(f"{item['type']}: {item['normalized_value']} [{item.get('source_document_id', '')}]")
            elif "summary" in item:
                summaries.append(f"{item['summary']} [{item.get('source_document_id', '')}]")
            elif "test" in item:
                summaries.append(f"{item['test']}: {item['value']} {item.get('unit','')} [{item.get('document_id','')}]")
        answer += "; ".join(summaries) + "."

        return DoctorQAResponse(
            question=question,
            interpreted_pattern=pattern,
            answer=answer,
            source_references=sources,
            retrieved_evidence=evidence,
            data_available=True,
            confidence=0.9
        )


doctor_qa_service = DoctorQAService()
