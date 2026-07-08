from dataclasses import dataclass


@dataclass
class RawDocument:
    doc_id: str
    text: str
    doc_type: str  # "radiology_report" | "discharge_summary" | "guideline" | "mtsample"
    source_path: str
    specialty: str | None = None
    patient_id: str | None = None
    report_date: str | None = None


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    section_type: str | None
    chunk_index: int
    doc_type: str
    patient_id: str | None
    report_date: str | None