from pathlib import Path

import fitz
import pdfplumber
from pdfminer.high_level import extract_text


# ==================================================
# PROJECT PATHS
# ==================================================

ROOT = Path.cwd()

RAW_RESUME_DIR = ROOT / "data" / "raw_resumes"

OUTPUT_DIR = (
    ROOT
    / "evaluation"
    / "result_text_extraction"
    / "data"
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

    pdf_files = [
    RAW_RESUME_DIR / f"R-{i:03d}.pdf"
    for i in range(1, 11)
]

    print(f"\nFound {len(pdf_files)} PDFs")

    for pdf_file in pdf_files:

        resume_name = pdf_file.stem

        print(f"\nProcessing {resume_name}")

        try:

            # --------------------------
            # PyMuPDF
            # --------------------------

            text = pymupdf_extract(
                pdf_file
            )

            save_text(
                text,
                PYMUPDF_DIR /
                f"{resume_name}.txt"
            )

            # --------------------------
            # pdfplumber
            # --------------------------

            text = pdfplumber_extract(
                pdf_file
            )

            save_text(
                text,
                PDFPLUMBER_DIR /
                f"{resume_name}.txt"
            )

            # --------------------------
            # pdfminer
            # --------------------------

            text = pdfminer_extract(
                pdf_file
            )

            save_text(
                text,
                PDFMINER_DIR /
                f"{resume_name}.txt"
            )

            print(
                f"SUCCESS: {resume_name}"
            )

        except Exception as e:

            print(
                f"FAILED: {resume_name}"
            )

            print(e)

    print("\nDone")


if __name__ == "__main__":
    main()