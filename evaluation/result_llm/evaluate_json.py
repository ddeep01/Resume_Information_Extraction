import json
import re
from pathlib import Path
import pandas as pd

from metrics_json import (
    field_similarity,
    object_similarity,
    list_of_dicts_score,
    count_field_score
)

ROOT = Path(__file__).parent

GT_DIR = ROOT / "data" / "ground_truth"

MODELS = [
    "llama3.1_8b",
    "mistral_7b",
    "qwen2.5_7b"
]

PERSONAL_FIELDS = [
    "full_name", "current_designation", "total_experience",
    "email", "phone", "date_of_birth", "gender", "address",
    "linkedin", "google_scholar", "researchgate"
]

EDUCATION_KEY_FIELDS = ["institution", "degree"]
EDUCATION_ALL_FIELDS = [
    "degree", "specialization", "institution",
    "board_university", "year", "cgpa_percentage", "normalized_degree"
]

EXPERIENCE_KEY_FIELDS = ["organization", "designation"]
EXPERIENCE_ALL_FIELDS = [
    "designation", "organization", "start_date",
    "end_date", "duration", "description"
]


def find_prediction_file(model_dir: Path, gt_file: Path) -> Path:
    """Find corresponding prediction file for a ground truth file."""
    direct = model_dir / gt_file.name
    if direct.exists():
        return direct

    # Extract number from GT filename (e.g. R-001_ground_truth.json -> 1)
    match = re.search(r'\d+', gt_file.name)
    if match:
        num = int(match.group())
        candidates = [
            f"Resume-{num:02d}.json",
            f"Resume-{num:03d}.json",
            f"Resume-{num}.json",
            f"R-{num:02d}.json",
            f"R-{num:03d}.json",
            f"R-{num}.json"
        ]
        for cand in candidates:
            p = model_dir / cand
            if p.exists():
                return p

    return direct


results = []

for model in MODELS:

    model_dir = ROOT / "data" / model

    print(f"\nEvaluating {model}...")

    for gt_file in sorted(GT_DIR.glob("*.json")):

        pred_file = find_prediction_file(model_dir, gt_file)

        gt = json.loads(gt_file.read_text(encoding="utf-8"))

        failure_row = {
            "resume": gt_file.stem,
            "model": model,
            "personal_info_score": 0.0,
            "education_precision": 0.0,
            "education_recall": 0.0,
            "education_f1": 0.0,
            "education_field_accuracy": 0.0,
            "experience_precision": 0.0,
            "experience_recall": 0.0,
            "experience_f1": 0.0,
            "experience_field_accuracy": 0.0,
            "publication_summary_score": 0.0,
            "highest_degree_score": 0.0,
            "overall_score": 0.0,
            "note": "missing_or_invalid_json"
        }

        if not pred_file.exists():
            print(f"  MISSING prediction for {gt_file.stem} ({pred_file.name}) — scoring as full failure")
            results.append(failure_row)
            continue

        try:
            pred = json.loads(pred_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  INVALID JSON for {gt_file.stem} ({pred_file.name}) — scoring as full failure")
            results.append(failure_row)
            continue

        print(f"  Matched {gt_file.name} -> {pred_file.name}")

        personal_score = object_similarity(
            gt.get("personal_information", {}),
            pred.get("personal_information", {}),
            PERSONAL_FIELDS
        )

        edu_scores = list_of_dicts_score(
            gt.get("education", []),
            pred.get("education", []),
            EDUCATION_KEY_FIELDS,
            EDUCATION_ALL_FIELDS
        )

        exp_scores = list_of_dicts_score(
            gt.get("experience", []),
            pred.get("experience", []),
            EXPERIENCE_KEY_FIELDS,
            EXPERIENCE_ALL_FIELDS
        )

        pub_score = count_field_score(
            gt.get("publication_summary", {}),
            pred.get("publication_summary", {})
        )

        highest_degree_score = field_similarity(
            gt.get("normalized_highest_degree", ""),
            pred.get("normalized_highest_degree", "")
        )

        # Composite overall score across non-None sections
        key_metrics = [
            personal_score,
            edu_scores["f1"],
            edu_scores["field_accuracy"],
            exp_scores["f1"],
            exp_scores["field_accuracy"],
            pub_score,
            highest_degree_score
        ]
        valid_metrics = [m for m in key_metrics if m is not None]
        overall_score = sum(valid_metrics) / len(valid_metrics) if valid_metrics else 0.0

        row = {
            "resume": gt_file.stem,
            "pred_file": pred_file.name,
            "model": model,

            "personal_info_score": personal_score,

            "education_precision": edu_scores["precision"],
            "education_recall": edu_scores["recall"],
            "education_f1": edu_scores["f1"],
            "education_field_accuracy": edu_scores["field_accuracy"],

            "experience_precision": exp_scores["precision"],
            "experience_recall": exp_scores["recall"],
            "experience_f1": exp_scores["f1"],
            "experience_field_accuracy": exp_scores["field_accuracy"],

            "publication_summary_score": pub_score,
            "highest_degree_score": highest_degree_score,
            "overall_score": overall_score,
            "note": "ok"
        }

        results.append(row)

df = pd.DataFrame(results)

RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(exist_ok=True)

df.to_csv(RESULT_DIR / "per_resume_metrics.csv", index=False)

summary = (
    df.groupby("model")
    .mean(numeric_only=True)
    .reset_index()
)

summary.to_csv(RESULT_DIR / "summary_metrics.csv", index=False)

print("\n" + "=" * 80)
print("LLM JSON EXTRACTION EVALUATION SUMMARY")
print("=" * 80)
print(summary.to_string(index=False))
print("=" * 80)
print(f"\nSaved per-resume results to: {RESULT_DIR / 'per_resume_metrics.csv'}")
print(f"Saved summary metrics to:    {RESULT_DIR / 'summary_metrics.csv'}\n")