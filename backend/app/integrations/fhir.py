import uuid
import datetime
from typing import Dict, Any, List

class FHIRConverter:
    """
    Converts MediKiosk clinical histories and document lab extractions
    into HL7 FHIR R4 interoperable JSON Bundles compatible with ABDM Health Information Exchange.
    """
    def build_fhir_bundle(
        self,
        patient_data: Dict[str, Any],
        history_data: Dict[str, Any],
        lab_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        
        patient_id = patient_data.get("patient_id", str(uuid.uuid4()))
        bundle_id = f"urn:uuid:{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        # 1. FHIR Patient Resource
        fhir_patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [
                {
                    "system": "https://healthid.ndhm.gov.in",
                    "value": patient_data.get("abha_id", f"ABHA-{patient_id[:8]}")
                }
            ],
            "name": [{"text": patient_data.get("name", "Unknown Patient")}],
            "gender": patient_data.get("gender", "unknown").lower(),
            "telecom": [{"system": "phone", "value": patient_data.get("phone", "")}]
        }

        # 2. FHIR Condition Resource (Chief Complaint / HPI)
        fhir_condition = {
            "resourceType": "Condition",
            "id": f"cond-{patient_id[:8]}",
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "category": [
                {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]
                }
            ],
            "code": {
                "text": history_data.get("chief_complaint", "General Consultation Intake")
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "recordedDate": timestamp
        }

        # 3. FHIR Observation Resources (Lab Results)
        observations = []
        for idx, lab in enumerate(lab_results):
            obs = {
                "resourceType": "Observation",
                "id": f"obs-{patient_id[:8]}-{idx}",
                "status": "final",
                "category": [
                    {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]
                    }
                ],
                "code": {"text": lab.get("test_name", "Laboratory Measurement")},
                "subject": {"reference": f"Patient/{patient_id}"},
                "valueQuantity": {
                    "value": float(lab.get("value", 0.0)) if str(lab.get("value")).replace('.', '', 1).isdigit() else lab.get("value"),
                    "unit": lab.get("unit", "")
                },
                "interpretation": [
                    {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": "H" if lab.get("abnormal") else "N"
                        }]
                    }
                ]
            }
            observations.append(obs)

        # Build complete FHIR Bundle
        entries = [
            {"fullUrl": f"urn:uuid:{patient_id}", "resource": fhir_patient},
            {"fullUrl": f"urn:uuid:cond-{patient_id[:8]}", "resource": fhir_condition}
        ]

        for obs in observations:
            entries.append({"fullUrl": f"urn:uuid:{obs['id']}", "resource": obs})

        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "document",
            "timestamp": timestamp,
            "entry": entries
        }

        return bundle

fhir_converter = FHIRConverter()
