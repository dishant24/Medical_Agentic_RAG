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