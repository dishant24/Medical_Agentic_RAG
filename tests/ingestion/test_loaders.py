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