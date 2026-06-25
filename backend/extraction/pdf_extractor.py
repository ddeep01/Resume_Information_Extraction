from pathlib import Path
import fitz
import pdfplumber


class PDFExtractor:

    MIN_TEXT_LENGTH = 100

    @staticmethod
    def extract_pymupdf(pdf_path):

        try:
            text_parts = []

            with fitz.open(pdf_path) as doc:

                for page in doc:
                    text_parts.append(page.get_text())

            return "\n".join(text_parts).strip()

        except Exception as e:
            print(f"PyMuPDF Error: {pdf_path} -> {e}")
            return ""

    @staticmethod
    def extract_pdfplumber(pdf_path):

        try:
            text_parts = []

            with pdfplumber.open(pdf_path) as pdf:

                for page in pdf.pages:

                    page_text = page.extract_text()

                    if page_text:
                        text_parts.append(page_text)

            return "\n".join(text_parts).strip()

        except Exception as e:
            print(f"pdfplumber Error: {pdf_path} -> {e}")
            return ""

    @classmethod
    def extract(cls, pdf_path):

        text = cls.extract_pymupdf(pdf_path)

        if len(text) >= cls.MIN_TEXT_LENGTH:
            return text, "pymupdf"

        text = cls.extract_pdfplumber(pdf_path)

        if len(text) >= cls.MIN_TEXT_LENGTH:
            return text, "pdfplumber"

        return "", "failed"


RAW_DIR = Path("data/raw_resumes")
OUTPUT_DIR = Path("data/extracted_text")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def process_all_resumes():

    pdf_files = list(RAW_DIR.glob("*.pdf"))

    print(f"\nFound {len(pdf_files)} PDF files\n")

    success = 0
    failed = 0

    for pdf_file in pdf_files:

        text, method = PDFExtractor.extract(
            str(pdf_file)
        )

        if method == "failed":

            failed += 1

            print(
                f"[FAILED] {pdf_file.name}"
            )

            continue

        output_file = (
            OUTPUT_DIR /
            f"{pdf_file.stem}.txt"
        )

        output_file.write_text(
            text,
            encoding="utf-8"
        )

        success += 1

        print(
            f"[SUCCESS] {pdf_file.name} -> {method}"
        )

    print("\n" + "=" * 50)
    print(f"Total Files : {len(pdf_files)}")
    print(f"Success     : {success}")
    print(f"Failed      : {failed}")
    print("=" * 50)


if __name__ == "__main__":
    process_all_resumes()