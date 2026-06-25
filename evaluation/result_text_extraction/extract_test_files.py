from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]

GROUND_TRUTH = ROOT / "data" / "groundt_truth"
EXTRACTED = ROOT / "data" / "extracted_text"

DEST = Path(__file__).parent / "data"

TOOLS = [
    "pymupdf",
    "pdfplumber",
    "pdfminer"
]

for tool in TOOLS:
    (DEST / tool).mkdir(
        parents=True,
        exist_ok=True
    )

(DEST / "ground_truth").mkdir(
    parents=True,
    exist_ok=True
)

for gt_file in GROUND_TRUTH.glob("*.txt"):

    resume_name = gt_file.name

    shutil.copy2(
        gt_file,
        DEST / "ground_truth" / resume_name
    )

    for tool in TOOLS:

        src = EXTRACTED / tool / resume_name

        if src.exists():

            shutil.copy2(
                src,
                DEST / tool / resume_name
            )

print("Files copied successfully")