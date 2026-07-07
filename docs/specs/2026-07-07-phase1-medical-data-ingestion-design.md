# Phase 1: Medical Data Ingestion — Design

## Goal

Produce a clean, chunked, metadata-rich dataset (`data/processed/chunks.jsonl`)
from raw clinical documents, ready for embedding in Phase 2. No embeddings or
vector storage happens in this phase — output is text chunks with metadata.

## Data Sources

- **MTSamples** (public, no login) — filtered to Radiology and Discharge
  Summary / General Medicine specialties, ~50-100 reports. Small subset
  chosen deliberately for fast iteration while the pipeline is still being
  built and debugged; can be widened later once the pipeline is proven.
- **Public clinical guideline PDFs** (2-3 documents, e.g. WHO/NICE) — used as
  the cross-reference target for multi-hop questions ("what did the guideline
  recommend").
- **Hand-authored patient timelines** (~3-5 fictional patients, 2-3 dated
  reports each, plain `.txt` files) — public sources don't link documents
  into a patient timeline, but the target multi-hop query pattern ("what
  changed between this patient's last two scans") requires one. These are
  small, clearly fictional fixtures written specifically to make that class
  of question answerable and checkable later (Phase 3 eval set draws directly
  from these).

Exact MTSamples/guideline download URLs are not pinned in this spec — they
will be located via web search at implementation time and confirmed before
downloading, rather than guessed.

## Architecture

An offline batch pipeline (not a live service): **acquire raw docs** →
**load into a common structure** → **chunk with section-awareness** →
write to `data/processed/chunks.jsonl`.

```
src/medrag/ingestion/
├── models.py       # RawDocument, Chunk dataclasses
├── loaders.py      # CSV (MTSamples), PDF (guidelines), TXT (patient timelines) -> RawDocument
├── chunking.py     # section-aware chunker -> list[Chunk]
└── pipeline.py     # orchestrates: raw docs -> chunks.jsonl

data/raw/
├── mtsamples/            # filtered CSV subset
├── guidelines/            # guideline PDFs
└── patient_timelines/     # hand-authored .txt scenarios, one folder per patient

data/processed/
└── chunks.jsonl           # one JSON object per line
```

## Data Model

```python
@dataclass
class RawDocument:
    doc_id: str
    text: str
    doc_type: str          # "radiology_report" | "discharge_summary" | "guideline" | "mtsample"
    source_path: str
    specialty: str | None = None
    patient_id: str | None = None   # only set for hand-authored timeline docs
    report_date: str | None = None  # only set for hand-authored timeline docs

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    section_type: str | None   # "FINDINGS" | "IMPRESSION" | "HISTORY" | ... | None
    chunk_index: int
    doc_type: str
    patient_id: str | None
    report_date: str | None
```

Every chunk carries its parent document's metadata, so later retrieval can
filter/boost by section type or pull a specific patient's most recent reports
without re-parsing raw text.

## Chunking Algorithm

For each `RawDocument`:

1. Regex-detect known clinical section headers (`FINDINGS:`, `IMPRESSION:`,
   `HISTORY:`, `HOSPITAL COURSE:`, `CHIEF COMPLAINT:`, `DISCHARGE
   MEDICATIONS:`, etc. — a small fixed list covering radiology reports and
   discharge summaries) and split the document at those boundaries first.
2. Any resulting section still over ~500 characters is recursively split
   with overlap (sentence-aware, same technique as generic RAG chunking).
3. Documents with no recognized headers (e.g. guideline prose) fall through
   entirely to step 2's size-based splitting; `section_type=None` for those
   chunks.

## Error Handling

Offline batch job, not a live service — fail loud per-item, not silently or
catastrophically for the whole run. A malformed CSV row or unreadable PDF is
logged and skipped; the pipeline reports a summary count at the end
(`processed: N, skipped: M`).

## Testing Strategy

pytest fixtures using small hand-written sample text per doc type:

- A fake radiology report with recognized headers — assert exact chunk
  boundaries and `section_type` values.
- A header-less guideline paragraph — assert fallback to size-based
  splitting with `section_type=None`.
- A section deliberately longer than ~500 characters — assert it gets
  sub-split with overlap rather than left as one oversized chunk.
- Each loader (CSV/PDF/TXT) tested against a small fixture file, asserting
  correct `RawDocument` fields.
- Pipeline end-to-end test: small fixture directory in → expected
  `chunks.jsonl` structure out.

## Out of Scope

No embeddings, no vector storage, no FAISS/BM25 — that's Phase 2. No eval
set construction — that's Phase 3 (though it will draw on the hand-authored
patient timelines created here).
