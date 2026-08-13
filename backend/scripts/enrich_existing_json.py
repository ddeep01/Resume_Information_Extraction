"""
==============================================================================
Script: Enrich Existing JSON Datasets
==============================================================================

Purpose
-------
Iterate over all extracted JSON files in evaluation and data directories and
add `normalized_degree` (to each education item) and `normalized_highest_degree`
(to top level) without modifying original raw degree fields.
==============================================================================
"""

import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

from degree_normalizer import normalize_candidate_json


def process_json_directory(dir_path: Path):
    if not dir_path.exists():
        print(f"Directory not found: {dir_path}")
        return

    json_files = list(dir_path.glob("*.json"))
    print(f"Processing {len(json_files)} files in {dir_path}...")

    count = 0
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            enriched = normalize_candidate_json(data)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=4, ensure_ascii=False)

            count += 1
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    print(f"Successfully enriched {count} files in {dir_path.name}\n")


def main():
    target_dirs = [
        ROOT / "evaluation" / "result_llm" / "data" / "qwen2.5_7b",
        ROOT / "evaluation" / "result_llm" / "data" / "llama3.1_8b",
        ROOT / "evaluation" / "result_llm" / "data" / "mistral_7b",
        ROOT / "evaluation" / "result_llm" / "data" / "ground_truth",
        ROOT / "data" / "extracted_json",
    ]

    for d in target_dirs:
        process_json_directory(d)


if __name__ == "__main__":
    main()
