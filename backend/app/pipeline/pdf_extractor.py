import logging
from pathlib import Path
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text as pdfminer_extract_text

logger = logging.getLogger("PDFExtractor")

class PDFExtractor:
    MIN_TEXT_LENGTH = 100

    @staticmethod
    def extract_pymupdf(pdf_path: Path) -> str:
        try:
            text_parts = []
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts).strip()
        except Exception as e:
            logger.warning(f"PyMuPDF error for {pdf_path}: {e}")
            return ""

    @staticmethod
    def extract_pdfminer(pdf_path: Path) -> str:
        try:
            text = pdfminer_extract_text(str(pdf_path))
            return text.strip() if text else ""
        except Exception as e:
            logger.warning(f"PDFMiner error for {pdf_path}: {e}")
            return ""

    @staticmethod
    def extract_ocr(pdf_path: Path) -> str:
        """
        Optional OCR fallback using pytesseract and pdf2image if available.
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path
            images = convert_from_path(str(pdf_path))
            ocr_text = []
            for img in images:
                ocr_text.append(pytesseract.image_to_string(img))
            return "\n".join(ocr_text).strip()
        except Exception as e:
            logger.warning(f"OCR fallback unavailable or failed for {pdf_path}: {e}")
            return ""

    @classmethod
    def extract(cls, pdf_path: Path) -> tuple[str, str]:
        """
        Extract text from PDF using multi-stage strategy.
        Returns: (extracted_text, method_used)
        """
        pdf_path = Path(pdf_path)
        
        # 1. Try PyMuPDF
        text = cls.extract_pymupdf(pdf_path)
        if len(text) >= cls.MIN_TEXT_LENGTH:
            return text, "pymupdf"

        # 2. Try PDFMiner
        text = cls.extract_pdfminer(pdf_path)
        if len(text) >= cls.MIN_TEXT_LENGTH:
            return text, "pdfminer"

        # 3. Try OCR
        text = cls.extract_ocr(pdf_path)
        if len(text) >= cls.MIN_TEXT_LENGTH:
            return text, "ocr"

        # Return whatever was extracted even if short
        return text, "pymupdf_short" if text else "failed"
