import csv
import logging
from pathlib import Path

from pypdf import PdfReader

from medrag.ingestion.models import RawDocument

logger = logging.getLogger(__name__)

_SPECIALTY_TO_DOC_TYPE = {
    "Radiology": "radiology_report",
    "Discharge Summary": "discharge_summary",
}


def load_mtsamples_csv(path: Path) -> list[RawDocument]:
    docs: list[RawDocument] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                specialty = row["medical_specialty"].strip()
                doc_type = _SPECIALTY_TO_DOC_TYPE.get(specialty, "mtsample")
                docs.append(
                    RawDocument(
                        doc_id=f"mtsample_{i}",
                        text=row["transcription"] or "",
                        doc_type=doc_type,
                        source_path=str(path),
                        specialty=specialty,
                    )
                )
            except (KeyError, AttributeError) as exc:
                logger.warning("Skipping malformed MTSamples row %d: %s", i, exc)
    return docs


def load_guideline_pdf(path: Path) -> RawDocument:
    text = _extract_pdf_text(path)
    return RawDocument(
        doc_id=path.stem,
        text=text,
        doc_type="guideline",
        source_path=str(path),
    )


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_patient_timeline_txt(path: Path) -> RawDocument:
    patient_id = path.parent.name
    report_date = path.stem.split("_", 1)[0]
    text = path.read_text(encoding="utf-8")
    return RawDocument(
        doc_id=f"{patient_id}_{report_date}",
        text=text,
        doc_type="radiology_report",
        source_path=str(path),
        patient_id=patient_id,
        report_date=report_date,
    )