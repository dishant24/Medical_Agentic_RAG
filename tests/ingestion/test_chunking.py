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