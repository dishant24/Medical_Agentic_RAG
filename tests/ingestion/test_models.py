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