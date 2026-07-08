import json
import logging
from pathlib import Path

from medrag.ingestion.chunking import chunk_document
from medrag.ingestion.loaders import (
    load_guideline_pdf,
    load_mtsamples_csv,
    load_patient_timeline_txt,
)
from medrag.ingestion.models import RawDocument

logger = logging.getLogger(__name__)


def run_pipeline(raw_dir: Path, output_path: Path) -> dict[str, int]:
    docs, skipped = _load_all_documents(raw_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for doc in docs:
            for chunk in chunk_document(doc):
                f.write(json.dumps(chunk.__dict__) + "\n")
                chunk_count += 1

    return {"documents": len(docs), "chunks": chunk_count, "skipped": skipped}


def _load_all_documents(raw_dir: Path) -> tuple[list[RawDocument], int]:
    docs: list[RawDocument] = []
    skipped = 0

    mtsamples_csv = raw_dir / "mtsamples" / "mtsamples_filtered.csv"
    if mtsamples_csv.exists():
        docs.extend(load_mtsamples_csv(mtsamples_csv))

    for pdf_path in sorted((raw_dir / "guidelines").glob("*.pdf")):
        try:
            docs.append(load_guideline_pdf(pdf_path))
        except Exception as exc:
            logger.warning("Skipping unreadable guideline PDF %s: %s", pdf_path, exc)
            skipped += 1

    for txt_path in sorted((raw_dir / "patient_timelines").glob("*/*.txt")):
        try:
            docs.append(load_patient_timeline_txt(txt_path))
        except Exception as exc:
            logger.warning("Skipping unreadable patient timeline file %s: %s", txt_path, exc)
            skipped += 1

    return docs, skipped