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