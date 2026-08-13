from pathlib import Path

import fitz
import pdfplumber
from pdfminer.high_level import extract_text


# ==================================================
# PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_RESUME_DIR = ROOT / "data" / "raw_resumes"

OUTPUT_DIR = (
    Path(__file__).parent / "data"
)

PYMUPDF_DIR = OUTPUT_DIR / "pymupdf"
PDFPLUMBER_DIR = OUTPUT_DIR / "pdfplumber"
PDFMINER_DIR = OUTPUT_DIR / "pdfminer"

PYMUPDF_DIR.mkdir(parents=True, exist_ok=True)
PDFPLUMBER_DIR.mkdir(parents=True, exist_ok=True)
PDFMINER_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# EXTRACTORS
# ==================================================

def pymupdf_extract(pdf_path):

    text = []

    doc = fitz.open(pdf_path)

    for page in doc:

        page_text = page.get_text()

        if page_text:
            text.append(page_text)

    doc.close()

    return "\n".join(text)


def pdfplumber_extract(pdf_path):

    text = []

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text.append(page_text)

    return "\n".join(text)


def pdfminer_extract(pdf_path):

    return extract_text(str(pdf_path))


# ==================================================
# SAVE
# ==================================================

def save_text(text, output_file):

    output_file.write_text(
        text,
        encoding="utf-8",
        errors="ignore"
    )


# ==================================================
# MAIN
# ==================================================

def main():

    # Target 10 test resumes: Resume-01.pdf through Resume-10.pdf
    pdf_files = [
        RAW_RESUME_DIR / f"Resume-{i:02d}.pdf"
        for i in range(1, 11)
    ]

    # Fallback if Resume-X pattern isn't found
    pdf_files = [f for f in pdf_files if f.exists()]
    if not pdf_files:
        pdf_files = sorted(RAW_RESUME_DIR.glob("*.pdf"))[:10]

    print(f"\nFound {len(pdf_files)} Test PDFs for extraction benchmark\n")

    for pdf_file in pdf_files:

        resume_name = pdf_file.stem

        print(f"Processing {resume_name}...")

        try:

            # 1. PyMuPDF
            text = pymupdf_extract(pdf_file)
            save_text(text, PYMUPDF_DIR / f"{resume_name}.txt")

            # 2. pdfplumber
            text = pdfplumber_extract(pdf_file)
            save_text(text, PDFPLUMBER_DIR / f"{resume_name}.txt")

            # 3. pdfminer
            text = pdfminer_extract(pdf_file)
            save_text(text, PDFMINER_DIR / f"{resume_name}.txt")

            print(f"  [SUCCESS] {resume_name}")

        except Exception as e:

            print(f"  [FAILED] {resume_name}: {e}")

    print("\nExtraction finished for all 3 libraries.")


if __name__ == "__main__":
    main()
