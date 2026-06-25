from pathlib import Path
import pandas as pd

from metrics import (
    calculate_f1,
    calculate_cer,
    calculate_ned,
    calculate_bleu
)

ROOT = Path(__file__).parent

GT_DIR = (
    ROOT /
    "data" /
    "ground_truth"
)

TOOLS = [
    "pymupdf",
    "pdfplumber",
    "pdfminer"
]

results = []


for tool in TOOLS:

    tool_dir = (
        ROOT /
        "data" /
        tool
    )

    print(f"\nEvaluating {tool}")

    for gt_file in GT_DIR.glob("*.txt"):

        pred_file = (
            tool_dir /
            gt_file.name
        )

        if not pred_file.exists():
            continue

        gt_text = gt_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        pred_text = pred_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        row = {

            "resume":
            gt_file.stem,

            "tool":
            tool,

            "f1":
            calculate_f1(
                gt_text,
                pred_text
            ),

            "cer":
            calculate_cer(
                gt_text,
                pred_text
            ),

            "bleu":
            calculate_bleu(
                gt_text,
                pred_text
            ),

            "ned":
            calculate_ned(
                gt_text,
                pred_text
            )
        }

        results.append(row)

df = pd.DataFrame(results)

RESULT_DIR = (
    ROOT /
    "results"
)

RESULT_DIR.mkdir(
    exist_ok=True
)

# Detailed Results
df.to_csv(
    RESULT_DIR /
    "per_resume_metrics.csv",
    index=False
)

# Summary Results
summary = (
    df.groupby("tool")
    .mean(
        numeric_only=True
    )
    .reset_index()
)

summary.to_csv(
    RESULT_DIR /
    "summary_metrics.csv",
    index=False
)

print("\n")
print(summary)

print(
    "\nSaved Results Successfully"
)