import pytest
from pathlib import Path
from backend.app.pipeline.preprocessor import ResumeTextCleaner
from backend.app.pipeline.docx_extractor import DOCXExtractor
from backend.app.pipeline.pdf_extractor import PDFExtractor

def test_text_cleaner():
    cleaner = ResumeTextCleaner()
    raw = "John   Doe\nﬁrst page\r\n\r\n\r\n- Bullet item\t\ncom-\nputer science"
    cleaned = cleaner.clean(raw)
    assert "first page" in cleaned
    assert "computer science" in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned

def test_docx_extractor_non_existent():
    text, method = DOCXExtractor.extract_docx(Path("non_existent.docx"))
    assert method == "failed"
    assert text == ""

def test_pdf_extractor_non_existent():
    text, method = PDFExtractor.extract(Path("non_existent.pdf"))
    assert method in ["failed", "pymupdf_short"]
