import fitz

from app.rag.chunking import chunk_pages
from app.rag.pdf_processor import PageContent, extract_pdf
from app.rag.text_extractor import canonical_standard_number, detect_clause_heading, find_standard_numbers
from app.tests.conftest import SYNTHETIC_TEXT


def test_standard_number_normalisation():
    assert canonical_standard_number("is 1293:2019") == "IS 1293:2019"
    assert canonical_standard_number("IS 302 (part 1) : 2008") == "IS 302 (Part 1):2008"
    assert find_standard_numbers("See IS 99999 : 2024 and IS 12345.") == ["IS 99999:2024", "IS 12345"]


def test_clause_heading_detection():
    assert detect_clause_heading("4.1 Material") == ("4.1", "Material")
    assert detect_clause_heading("ANNEX A") == ("Annex A", "")
    assert detect_clause_heading("4.5 mm") is None
    assert detect_clause_heading("12") is None
    assert detect_clause_heading("The widget shall be tested.") is None


def test_structure_aware_chunking_keeps_clause_metadata():
    chunks = chunk_pages([PageContent(page_number=3, text=SYNTHETIC_TEXT)])
    clauses = {c.clause_number for c in chunks}
    assert {"4.1", "5.1"} <= clauses or {"4", "5"} <= {c.split(".")[0] for c in clauses if c}
    assert all(c.page_number == 3 for c in chunks)
    material = next(c for c in chunks if "stainless steel" in c.text)
    assert material.clause_number and material.clause_number.startswith("4")
    assert material.section and "REQUIREMENTS" in material.section.upper()


def test_long_clause_is_split():
    long_text = "4.1 Material\n" + "\n".join(f"Sentence number {i} describing a requirement in detail." for i in range(200))
    chunks = chunk_pages([PageContent(page_number=1, text=long_text)])
    assert len(chunks) > 1
    assert all(len(c.text) <= 2100 for c in chunks)
    assert all(c.clause_number == "4.1" for c in chunks)


def test_pdf_extraction(tmp_path):
    path = tmp_path / "synthetic.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), SYNTHETIC_TEXT, fontsize=10)
    doc.set_metadata({"title": "Synthetic Widget Standard"})
    doc.save(path)
    doc.close()

    extracted = extract_pdf(path)
    assert extracted.page_count == 1
    assert extracted.title == "Synthetic Widget Standard"
    assert "stainless steel" in extracted.full_text
    assert not extracted.used_ocr
