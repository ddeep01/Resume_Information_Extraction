from pathlib import Path
import json
import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

ROOT = Path(__file__).resolve().parents[2]

EXTRACTED_DIR = ROOT / "data" / "extracted_text"
CLEANED_DIR = ROOT / "data" / "cleaned_text"

RESULT_DIR = Path(__file__).parent / "report"

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================================
# REPORT
# ==========================================================


def analyze_file(raw_text, clean_text):

    raw_lines = raw_text.splitlines()
    clean_lines = clean_text.splitlines()

    return {

        "characters_before": len(raw_text),

        "characters_after": len(clean_text),

        "words_before": len(raw_text.split()),

        "words_after": len(clean_text.split()),

        "lines_before": len(raw_lines),

        "lines_after": len(clean_lines),

        "characters_removed":
            len(raw_text) - len(clean_text),

        "words_removed":
            len(raw_text.split())
            - len(clean_text.split()),

        "lines_removed":
            len(raw_lines)
            - len(clean_lines),

        "compression_ratio":
            round(
                len(clean_text)
                / max(len(raw_text), 1),
                4,
            )
    }


# ==========================================================
# MAIN
# ==========================================================


def main():

    rows = []

    total_before = 0
    total_after = 0

    txt_files = sorted(
        EXTRACTED_DIR.glob("*.txt")
    )

    print(
        f"\nFound {len(txt_files)} files"
    )

    for raw_file in txt_files:

        clean_file = (
            CLEANED_DIR /
            raw_file.name
        )

        if not clean_file.exists():

            print(
                f"Missing cleaned file : {raw_file.name}"
            )

            continue

        raw_text = raw_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        clean_text = clean_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        report = analyze_file(
            raw_text,
            clean_text
        )

        report["resume"] = raw_file.stem

        rows.append(report)

        total_before += len(raw_text)

        total_after += len(clean_text)

    df = pd.DataFrame(rows)

    csv_path = (
        RESULT_DIR /
        "cleaning_report.csv"
    )

    df.to_csv(
        csv_path,
        index=False
    )

    summary = {

        "total_resumes":
            len(df),

        "total_characters_before":
            total_before,

        "total_characters_after":
            total_after,

        "characters_removed":
            total_before - total_after,

        "average_compression_ratio":
            round(
                df["compression_ratio"].mean(),
                4
            )
            if len(df)
            else 0,

        "average_characters_removed":
            round(
                df["characters_removed"].mean(),
                2
            )
            if len(df)
            else 0,

        "average_words_removed":
            round(
                df["words_removed"].mean(),
                2
            )
            if len(df)
            else 0,

        "average_lines_removed":
            round(
                df["lines_removed"].mean(),
                2
            )
            if len(df)
            else 0

    }

    json_path = (
        RESULT_DIR /
        "summary.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=4
        )

    print("\nCleaning Report Generated")

    print(csv_path)

    print(json_path)


if __name__ == "__main__":

    main()