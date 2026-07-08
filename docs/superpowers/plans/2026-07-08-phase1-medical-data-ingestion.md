# Phase 1: Medical Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `data/processed/chunks.jsonl` — section-aware chunks with metadata — from three real sources: a filtered MTSamples subset, two public NICE guideline PDFs, and three hand-authored fictional patient timelines.

**Architecture:** Three ingestion modules (`models.py`, `loaders.py`, `chunking.py`) orchestrated by `pipeline.py`, all under `src/medrag/ingestion/`. Two standalone one-off scripts under `scripts/` acquire raw data (not part of the tested package — they're run once, not imported).

**Tech Stack:** `pypdf` (PDF text extraction), `reportlab` (dev-only, generates PDF fixtures in tests), Python stdlib `csv`/`urllib` for everything else — no `pandas`, no `requests`, kept minimal on purpose.

**Real-data finding baked into this plan:** MTSamples' `transcription` field encodes section breaks as literal commas (`FINDINGS: , ...,IMPRESSION: , ...`), not newlines. Confirmed by downloading the real CSV and inspecting it directly (verified `,description,medical_specialty,sample_name,transcription,keywords` columns; specialty counts: Radiology=273, Discharge Summary=108; header tokens FINDINGS/IMPRESSION/HISTORY/CHIEF COMPLAINT/HOSPITAL COURSE/etc. all appear, but only after a comma, not a newline). The chunker's header regex must treat a preceding comma the same as a preceding newline.

Two verified, working download URLs (checked via HTTP HEAD, both return `200`):
- MTSamples CSV mirror: `https://raw.githubusercontent.com/eshza/medicalTranscriptsKaggle/master/mtsamples.csv`
- NICE NG122 (lung cancer diagnosis/management) PDF: `https://www.nice.org.uk/guidance/ng122/resources/lung-cancer-diagnosis-and-management-pdf-66141655525573`
- NICE NG136 (hypertension) PDF: `https://www.nice.org.uk/guidance/ng136/resources/hypertension-in-adults-diagnosis-and-management-pdf-66141722710213`

---

### Task 1: Data model and PDF dependency

**Files:**
- Modify: `pyproject.toml` (adds `pypdf` runtime dep, `reportlab` dev dep)
- Create: `src/medrag/ingestion/__init__.py`
- Create: `src/medrag/ingestion/models.py`
- Create: `tests/ingestion/__init__.py`
- Create: `tests/ingestion/test_models.py`

- [ ] **Step 1: Add dependencies**

Run: `uv add pypdf`
Run: `uv add --dev reportlab`

- [ ] **Step 2: Create package directories**

Create empty file `src/medrag/ingestion/__init__.py`.
Create empty file `tests/ingestion/__init__.py`.

- [ ] **Step 3: Write the failing test for the data model**

Create `tests/ingestion/test_models.py`:

```python
from medrag.ingestion.models import Chunk, RawDocument


def test_raw_document_optional_fields_default_to_none():
    doc = RawDocument(
        doc_id="doc1",
        text="some text",
        doc_type="guideline",
        source_path="fake.pdf",
    )
    assert doc.specialty is None
    assert doc.patient_id is None
    assert doc.report_date is None


def test_chunk_holds_section_and_lineage_metadata():
    chunk = Chunk(
        chunk_id="doc1_0",
        document_id="doc1",
        text="chunk text",
        section_type="FINDINGS",
        chunk_index=0,
        doc_type="radiology_report",
        patient_id="patient_101",
        report_date="2026-01-15",
    )
    assert chunk.section_type == "FINDINGS"
    assert chunk.patient_id == "patient_101"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'medrag.ingestion.models'`

- [ ] **Step 5: Implement the data model**

Create `src/medrag/ingestion/models.py`:

```python
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/ingestion/test_models.py -v`
Expected: `2 passed`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/medrag/ingestion/__init__.py src/medrag/ingestion/models.py tests/ingestion/__init__.py tests/ingestion/test_models.py
git commit -m "Add ingestion data model (RawDocument, Chunk)"
```

---

### Task 2: Section-aware chunker

**Files:**
- Create: `src/medrag/ingestion/chunking.py`
- Create: `tests/ingestion/test_chunking.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/ingestion/test_chunking.py`:

```python
from medrag.ingestion.chunking import chunk_document
from medrag.ingestion.models import RawDocument


def test_chunk_document_splits_by_newline_delimited_headers():
    doc = RawDocument(
        doc_id="doc1",
        text=(
            "HISTORY: Patient presents with cough.\n"
            "FINDINGS: Clear lungs bilaterally.\n"
            "IMPRESSION: No acute findings."
        ),
        doc_type="radiology_report",
        source_path="fake.txt",
    )
    chunks = chunk_document(doc)
    assert [c.section_type for c in chunks] == ["HISTORY", "FINDINGS", "IMPRESSION"]
    assert chunks[0].text.strip() == "Patient presents with cough."
    assert chunks[2].text.strip() == "No acute findings."
    assert [c.chunk_index for c in chunks] == [0, 1, 2]


def test_chunk_document_splits_by_comma_delimited_headers():
    # MTSamples encodes section breaks as literal commas, not newlines.
    doc = RawDocument(
        doc_id="doc2",
        text="EXAM: , Ultrasound of the scrotum.,FINDINGS:  ,No abnormality detected.,IMPRESSION:  ,Normal study.",
        doc_type="mtsample",
        source_path="fake.csv",
    )
    chunks = chunk_document(doc)
    assert [c.section_type for c in chunks] == ["EXAM", "FINDINGS", "IMPRESSION"]


def test_chunk_document_falls_back_to_plain_split_without_headers():
    doc = RawDocument(
        doc_id="doc3",
        text=(
            "This is a guideline paragraph with no recognized section "
            "headers at all, just plain prose describing recommendations "
            "for clinical practice."
        ),
        doc_type="guideline",
        source_path="fake.pdf",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section_type is None


def test_chunk_document_splits_oversized_section_with_overlap():
    long_text = "FINDINGS: " + ("word " * 200)  # well over 500 chars
    doc = RawDocument(
        doc_id="doc4",
        text=long_text,
        doc_type="radiology_report",
        source_path="fake.txt",
    )
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    assert all(c.section_type == "FINDINGS" for c in chunks)
    assert all(len(c.text) <= 500 for c in chunks)
    # Overlap: the tail of chunk 0 should reappear at the head of chunk 1.
    assert chunks[0].text[-50:] in chunks[1].text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingestion/test_chunking.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'medrag.ingestion.chunking'`

- [ ] **Step 3: Implement the chunker**

Create `src/medrag/ingestion/chunking.py`:

```python
import re

from medrag.ingestion.models import Chunk, RawDocument

MAX_CHUNK_CHARS = 500
CHUNK_OVERLAP_CHARS = 100

# Headers observed in real radiology and discharge summary reports
# (confirmed against the actual MTSamples dataset).
SECTION_HEADERS = [
    "REASON FOR EXAM",
    "REASON FOR EXAMINATION",
    "CLINICAL HISTORY",
    "HISTORY OF PRESENT ILLNESS",
    "GENERAL EVALUATION",
    "PREOPERATIVE DIAGNOSIS",
    "PREOPERATIVE DIAGNOSES",
    "ADMISSION DIAGNOSIS",
    "ADMISSION DIAGNOSES",
    "ADMITTING DIAGNOSIS",
    "ADMITTING DIAGNOSES",
    "DISCHARGE DIAGNOSIS",
    "DISCHARGE DIAGNOSES",
    "DISCHARGE MEDICATIONS",
    "DISCHARGE DISPOSITION",
    "FINAL DIAGNOSES",
    "PRINCIPAL DIAGNOSIS",
    "CHIEF COMPLAINT",
    "HOSPITAL COURSE",
    "TECHNIQUE",
    "FINDINGS",
    "IMPRESSION",
    "INDICATIONS",
    "INDICATION",
    "PROCEDURE",
    "DIAGNOSIS",
    "EXAM",
    "HISTORY",
]

# MTSamples encodes section breaks as literal commas ("FINDINGS: , text,
# IMPRESSION: , text"), not newlines. Our own hand-authored/PDF text uses
# real newlines. Accept either (or start-of-string) as a valid boundary.
_HEADER_RE = re.compile(
    r"(?:^|[,\n])\s*(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r")\s*:\s*,?\s*"
)


def chunk_document(doc: RawDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    index = 0
    for section_type, section_text in _split_into_sections(doc.text):
        section_text = section_text.strip(" ,\n")
        if not section_text:
            continue
        for piece in _split_oversized(section_text):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}_{index}",
                    document_id=doc.doc_id,
                    text=piece,
                    section_type=section_type,
                    chunk_index=index,
                    doc_type=doc.doc_type,
                    patient_id=doc.patient_id,
                    report_date=doc.report_date,
                )
            )
            index += 1
    return chunks


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    preamble = text[: matches[0].start()].strip(" ,\n")
    if preamble:
        sections.append((None, preamble))

    for i, match in enumerate(matches):
        header = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((header, text[start:end]))

    return sections


def _split_oversized(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    pieces = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP_CHARS
    return pieces
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_chunking.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/medrag/ingestion/chunking.py tests/ingestion/test_chunking.py
git commit -m "Add section-aware chunker (TDD)"
```

---

### Task 3: Loaders (CSV, PDF, TXT)

**Files:**
- Create: `src/medrag/ingestion/loaders.py`
- Create: `tests/ingestion/test_loaders.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/ingestion/test_loaders.py`:

```python
import logging

from medrag.ingestion.loaders import (
    load_guideline_pdf,
    load_mtsamples_csv,
    load_patient_timeline_txt,
)


def test_load_mtsamples_csv_maps_specialty_to_doc_type(tmp_path):
    csv_path = tmp_path / "mtsamples_filtered.csv"
    csv_path.write_text(
        ",description,medical_specialty,sample_name,transcription,keywords\n"
        '0,desc1,Radiology,Sample 1,"EXAM: , CT chest.,FINDINGS: , Clear.",keyword1\n'
        '1,desc2,Discharge Summary,Sample 2,"CHIEF COMPLAINT: , Chest pain.",keyword2\n',
        encoding="utf-8",
    )

    docs = load_mtsamples_csv(csv_path)

    assert len(docs) == 2
    assert docs[0].doc_type == "radiology_report"
    assert docs[0].specialty == "Radiology"
    assert docs[1].doc_type == "discharge_summary"
    assert docs[1].specialty == "Discharge Summary"


def test_load_mtsamples_csv_skips_malformed_row_and_continues(tmp_path, caplog):
    csv_path = tmp_path / "mtsamples_filtered.csv"
    csv_path.write_text(
        ",description,medical_specialty,sample_name,transcription,keywords\n"
        '0,desc1,Radiology,Sample 1,"EXAM: , CT chest.,FINDINGS: , Clear.",keyword1\n'
        "1,desc2\n"  # malformed: row is missing medical_specialty/transcription columns
        '2,desc3,Discharge Summary,Sample 3,"CHIEF COMPLAINT: , Pain.",keyword3\n',
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING):
        docs = load_mtsamples_csv(csv_path)

    assert [d.doc_id for d in docs] == ["mtsample_0", "mtsample_2"]
    assert "Skipping malformed MTSamples row" in caplog.text


def test_load_guideline_pdf_extracts_text(tmp_path):
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "sample_guideline.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Guideline Recommendation")
    c.drawString(100, 730, "Patients with a stable pulmonary nodule should")
    c.drawString(100, 710, "continue routine surveillance imaging.")
    c.save()

    doc = load_guideline_pdf(pdf_path)

    assert doc.doc_type == "guideline"
    assert doc.doc_id == "sample_guideline"
    assert "Guideline Recommendation" in doc.text
    assert "surveillance imaging" in doc.text


def test_load_patient_timeline_txt_parses_patient_id_and_date(tmp_path):
    patient_dir = tmp_path / "patient_999"
    patient_dir.mkdir()
    report_path = patient_dir / "2026-01-15_ct_chest.txt"
    report_path.write_text(
        "HISTORY: Test patient.\nFINDINGS: Nothing acute.", encoding="utf-8"
    )

    doc = load_patient_timeline_txt(report_path)

    assert doc.patient_id == "patient_999"
    assert doc.report_date == "2026-01-15"
    assert doc.doc_type == "radiology_report"
    assert "Nothing acute" in doc.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingestion/test_loaders.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'medrag.ingestion.loaders'`

- [ ] **Step 3: Implement the loaders**

Create `src/medrag/ingestion/loaders.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_loaders.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/medrag/ingestion/loaders.py tests/ingestion/test_loaders.py
git commit -m "Add CSV/PDF/TXT loaders (TDD)"
```

---

### Task 4: Pipeline orchestration

**Files:**
- Create: `src/medrag/ingestion/pipeline.py`
- Create: `tests/ingestion/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ingestion/test_pipeline.py`:

```python
import json

from medrag.ingestion.pipeline import run_pipeline


def test_run_pipeline_produces_chunks_jsonl_from_all_sources(tmp_path):
    raw_dir = tmp_path / "raw"
    (raw_dir / "mtsamples").mkdir(parents=True)
    (raw_dir / "guidelines").mkdir(parents=True)
    (raw_dir / "patient_timelines" / "patient_001").mkdir(parents=True)

    (raw_dir / "mtsamples" / "mtsamples_filtered.csv").write_text(
        ",description,medical_specialty,sample_name,transcription,keywords\n"
        '0,desc,Radiology,Sample,"EXAM: , CT chest.,FINDINGS: , Clear lungs.",kw\n',
        encoding="utf-8",
    )

    from reportlab.pdfgen import canvas

    pdf_path = raw_dir / "guidelines" / "test_guideline.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Recommendation: annual follow-up.")
    c.save()

    (raw_dir / "patient_timelines" / "patient_001" / "2026-01-01_ct_chest.txt").write_text(
        "HISTORY: Routine follow-up.\nIMPRESSION: Stable nodule.", encoding="utf-8"
    )

    output_path = tmp_path / "processed" / "chunks.jsonl"
    stats = run_pipeline(raw_dir, output_path)

    assert stats["documents"] == 3
    assert stats["skipped"] == 0
    assert output_path.exists()

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == stats["chunks"]
    first_chunk = json.loads(lines[0])
    assert "chunk_id" in first_chunk
    assert "text" in first_chunk


def test_run_pipeline_skips_unreadable_pdf_and_reports_it(tmp_path, caplog):
    import logging

    raw_dir = tmp_path / "raw"
    (raw_dir / "mtsamples").mkdir(parents=True)
    (raw_dir / "guidelines").mkdir(parents=True)
    (raw_dir / "patient_timelines").mkdir(parents=True)

    # Not a real PDF -- pypdf will raise when trying to read it.
    (raw_dir / "guidelines" / "corrupt.pdf").write_text("not a pdf", encoding="utf-8")

    output_path = tmp_path / "processed" / "chunks.jsonl"
    with caplog.at_level(logging.WARNING):
        stats = run_pipeline(raw_dir, output_path)

    assert stats["documents"] == 0
    assert stats["skipped"] == 1
    assert "Skipping unreadable guideline PDF" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ingestion/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'medrag.ingestion.pipeline'`

- [ ] **Step 3: Implement the pipeline**

Create `src/medrag/ingestion/pipeline.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_pipeline.py -v`
Expected: `2 passed`

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass (config tests from Phase 0 + all ingestion tests)

- [ ] **Step 6: Commit**

```bash
git add src/medrag/ingestion/pipeline.py tests/ingestion/test_pipeline.py
git commit -m "Add pipeline orchestration (TDD)"
```

---

### Task 5: Acquisition scripts and real downloads

**Files:**
- Create: `scripts/download_mtsamples.py`
- Create: `scripts/download_guidelines.py`

- [ ] **Step 1: Create the MTSamples acquisition script**

Create `scripts/download_mtsamples.py`:

```python
import csv
import random
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/eshza/medicalTranscriptsKaggle/master/mtsamples.csv"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "mtsamples"
KEEP_SPECIALTIES = {"Radiology", "Discharge Summary"}
SAMPLE_SIZE = 80
RANDOM_SEED = 42


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    full_csv_path = RAW_DIR / "mtsamples_full.csv"

    print(f"Downloading {SOURCE_URL} -> {full_csv_path}")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response, full_csv_path.open("wb") as f:
        f.write(response.read())

    with full_csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row["medical_specialty"].strip() in KEEP_SPECIALTIES]

    random.seed(RANDOM_SEED)
    sampled = random.sample(rows, min(SAMPLE_SIZE, len(rows)))

    filtered_path = RAW_DIR / "mtsamples_filtered.csv"
    with filtered_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sampled)

    full_csv_path.unlink()
    print(f"Wrote {len(sampled)} filtered reports to {filtered_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `uv run python scripts/download_mtsamples.py`
Expected: `Wrote 80 filtered reports to ...mtsamples_filtered.csv`

- [ ] **Step 3: Create the guideline acquisition script**

Create `scripts/download_guidelines.py`:

```python
import urllib.request
from pathlib import Path

GUIDELINES = {
    "nice_ng122_lung_cancer.pdf": "https://www.nice.org.uk/guidance/ng122/resources/lung-cancer-diagnosis-and-management-pdf-66141655525573",
    "nice_ng136_hypertension.pdf": "https://www.nice.org.uk/guidance/ng136/resources/hypertension-in-adults-diagnosis-and-management-pdf-66141722710213",
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "guidelines"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in GUIDELINES.items():
        dest = RAW_DIR / filename
        print(f"Downloading {url} -> {dest}")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request) as response, dest.open("wb") as f:
            f.write(response.read())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it**

Run: `uv run python scripts/download_guidelines.py`
Expected: two PDFs downloaded into `data/raw/guidelines/`

- [ ] **Step 5: Commit**

```bash
git add scripts/download_mtsamples.py scripts/download_guidelines.py
git commit -m "Add data acquisition scripts for MTSamples and NICE guidelines"
```

---

### Task 6: Hand-authored patient timelines, gitignore update, and full pipeline run

**Files:**
- Modify: `.gitignore`
- Create: `data/raw/patient_timelines/patient_101/2026-01-15_ct_chest.txt`
- Create: `data/raw/patient_timelines/patient_101/2026-04-10_ct_chest.txt`
- Create: `data/raw/patient_timelines/patient_102/2026-01-20_ct_chest.txt`
- Create: `data/raw/patient_timelines/patient_102/2026-04-18_ct_chest.txt`
- Create: `data/raw/patient_timelines/patient_103/2026-02-01_ct_chest.txt`
- Create: `data/raw/patient_timelines/patient_103/2026-05-15_ct_chest.txt`
- Delete: `data/raw/.gitkeep` (no longer needed — `patient_timelines/` will have real tracked files)
- Create: `data/raw/mtsamples/.gitkeep`
- Create: `data/raw/guidelines/.gitkeep`

- [ ] **Step 1: Update `.gitignore`**

Replace the existing `# Data` block (added in Phase 0) with:

```
# Data — mtsamples/guidelines are downloaded via script, not committed.
# patient_timelines/ is hand-authored source content and IS committed.
data/raw/mtsamples/*
data/raw/guidelines/*
data/processed/*
!data/raw/mtsamples/.gitkeep
!data/raw/guidelines/.gitkeep
!data/processed/.gitkeep
```

- [ ] **Step 2: Recreate `.gitkeep` placeholders for the still-ignored folders**

```bash
rm data/raw/.gitkeep
touch data/raw/mtsamples/.gitkeep data/raw/guidelines/.gitkeep
```

- [ ] **Step 3: Write patient 101 (stable nodule) — visit 1**

Create `data/raw/patient_timelines/patient_101/2026-01-15_ct_chest.txt`:

```
HISTORY: 58-year-old former smoker, incidental finding on prior chest X-ray.
TECHNIQUE: Non-contrast CT chest, 1.25mm axial reconstructions.
FINDINGS: A solid pulmonary nodule is present in the right upper lobe measuring 7mm in maximum diameter. No associated lymphadenopathy. No pleural effusion.
IMPRESSION: 7mm right upper lobe pulmonary nodule. Recommend follow-up low-dose CT in 3 months per Fleischner Society guidelines.
```

- [ ] **Step 4: Write patient 101 — visit 2 (unchanged)**

Create `data/raw/patient_timelines/patient_101/2026-04-10_ct_chest.txt`:

```
HISTORY: Follow-up of right upper lobe pulmonary nodule identified on prior CT dated 2026-01-15.
TECHNIQUE: Non-contrast CT chest, 1.25mm axial reconstructions.
FINDINGS: The previously described right upper lobe nodule again measures 7mm, unchanged from prior study. No new nodules identified. No lymphadenopathy.
IMPRESSION: Stable 7mm right upper lobe pulmonary nodule, unchanged over 3 months. Recommend routine annual follow-up.
```

- [ ] **Step 5: Write patient 102 (growing nodule) — visit 1**

Create `data/raw/patient_timelines/patient_102/2026-01-20_ct_chest.txt`:

```
HISTORY: 64-year-old current smoker, 40 pack-year history, incidental nodule on prior imaging.
TECHNIQUE: Non-contrast CT chest.
FINDINGS: Solid pulmonary nodule in the left lower lobe measuring 8mm. No mediastinal or hilar lymphadenopathy.
IMPRESSION: 8mm left lower lobe pulmonary nodule. Recommend follow-up CT in 3 months.
```

- [ ] **Step 6: Write patient 102 — visit 2 (grown, action required)**

Create `data/raw/patient_timelines/patient_102/2026-04-18_ct_chest.txt`:

```
HISTORY: Follow-up of left lower lobe pulmonary nodule, prior CT dated 2026-01-20.
TECHNIQUE: Non-contrast CT chest.
FINDINGS: The left lower lobe nodule has increased in size, now measuring 12mm, previously 8mm. No new nodules. No lymphadenopathy.
IMPRESSION: Interval growth of left lower lobe pulmonary nodule from 8mm to 12mm over 3 months. Recommend PET-CT and pulmonology referral for further evaluation given interval growth.
```

- [ ] **Step 7: Write patient 103 (new nodule at second scan) — visit 1**

Create `data/raw/patient_timelines/patient_103/2026-02-01_ct_chest.txt`:

```
HISTORY: 50-year-old nonsmoker, chest CT performed for unrelated abdominal workup.
TECHNIQUE: Non-contrast CT chest.
FINDINGS: Lungs are clear. No pulmonary nodules identified. No pleural effusion.
IMPRESSION: No pulmonary nodules. Normal chest CT.
```

- [ ] **Step 8: Write patient 103 — visit 2 (new finding)**

Create `data/raw/patient_timelines/patient_103/2026-05-15_ct_chest.txt`:

```
HISTORY: Follow-up chest CT for unrelated clinical indication, prior CT dated 2026-02-01 was normal.
TECHNIQUE: Non-contrast CT chest.
FINDINGS: A new solid nodule is identified in the right middle lobe measuring 9mm, not present on the prior study. No lymphadenopathy.
IMPRESSION: New 9mm right middle lobe pulmonary nodule, not present on prior CT from 2026-02-01. Recommend follow-up CT in 3 months given new finding in accordance with Fleischner Society guidelines for new solid nodules.
```

- [ ] **Step 9: Run the full pipeline against real data**

Run:
```bash
uv run python -c "from pathlib import Path; from medrag.ingestion.pipeline import run_pipeline; print(run_pipeline(Path('data/raw'), Path('data/processed/chunks.jsonl')))"
```
Expected: a dict like `{'documents': 88, 'chunks': <some number greater than documents>, 'skipped': 0}` (80 MTSamples + 2 guidelines + 6 patient timeline reports = 88 documents)

- [ ] **Step 10: Spot-check the output**

Run: `uv run python -c "import json; lines = open('data/processed/chunks.jsonl', encoding='utf-8').readlines(); print(len(lines)); print(json.loads(lines[0]))"`
Expected: prints total chunk count, then one chunk dict with `chunk_id`, `text`, `section_type`, `doc_type` fields populated

- [ ] **Step 11: Run the full test suite one more time**

Run: `uv run pytest -v`
Expected: all tests still pass

- [ ] **Step 12: Commit**

```bash
git add .gitignore data/raw/mtsamples/.gitkeep data/raw/guidelines/.gitkeep data/raw/patient_timelines/
git commit -m "Add hand-authored patient timelines; update gitignore for real data sources"
```

Note: `data/raw/mtsamples/mtsamples_filtered.csv`, `data/raw/guidelines/*.pdf`, and
`data/processed/chunks.jsonl` are gitignored by design — they're either downloaded
or generated, and reproducible by re-running the scripts/pipeline.
