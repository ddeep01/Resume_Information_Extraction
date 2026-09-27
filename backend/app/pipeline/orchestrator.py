from pathlib import Path
from backend.app.pipeline.pdf_extractor import PDFExtractor
from backend.app.pipeline.docx_extractor import DOCXExtractor
from backend.app.pipeline.preprocessor import ResumeTextCleaner

class ExtractionOrchestrator:
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.docx_extractor = DOCXExtractor()
        self.cleaner = ResumeTextCleaner()

    def process_file(self, file_path: Path) -> tuple[str, str, str]:
        """
        Process a single resume file (PDF or DOCX).
        Returns: (raw_text, cleaned_text, method_used)
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            raw_text, method = self.pdf_extractor.extract(file_path)
        elif suffix == ".docx":
            raw_text, method = self.docx_extractor.extract_docx(file_path)
        else:
            return "", "", "unsupported"

        cleaned_text = self.cleaner.clean(raw_text)
        return raw_text, cleaned_text, method
