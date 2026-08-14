from rapidfuzz import fuzz


def _to_str(val):
    """Safely convert any value to string, stripped of leading/trailing whitespace."""
    if val is None:
        return ""
    return str(val).strip()


def _to_num(val):
    """Safely convert any value to float/int, returning 0 if invalid."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return val
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return 0


def field_similarity(gt_val, pred_val):
    """Fuzzy similarity between two string fields. Returns None if GT is empty (N/A, not scored)."""
    gt_str = _to_str(gt_val)
    pred_str = _to_str(pred_val)

    if not gt_str:
        return None  # nothing in ground truth to check against — skip this field

    if not pred_str:
        return 0.0  # GT had a value, model produced nothing — full miss

    return fuzz.ratio(gt_str.lower(), pred_str.lower()) / 100.0


def object_similarity(gt_obj, pred_obj, fields):
    """Average field-level similarity across a list of field names, for one dict pair."""
    if not isinstance(gt_obj, dict):
        gt_obj = {}
    if not isinstance(pred_obj, dict):
        pred_obj = {}

    scores = []
    for f in fields:
        s = field_similarity(gt_obj.get(f), pred_obj.get(f))
        if s is not None:
            scores.append(s)
    return sum(scores) / len(scores) if scores else None


def match_list_entries(gt_list, pred_list, key_fields, match_threshold=0.5):
    """
    Greedily pair GT entries to predicted entries using similarity on key_fields
    (e.g. institution+degree for education, organization+designation for experience).
    Returns (matched_pairs, unmatched_gt_indices, unmatched_pred_indices).
    matched_pairs is a list of (gt_idx, pred_idx, key_score).
    """
    candidates = []
    for i, gt in enumerate(gt_list):
        if not isinstance(gt, dict):
            gt = {}
        for j, pred in enumerate(pred_list):
            if not isinstance(pred, dict):
                pred = {}

            key_gt_parts = [_to_str(gt.get(f)) for f in key_fields]
            key_gt = " ".join(part for part in key_gt_parts if part).lower()

            key_pred_parts = [_to_str(pred.get(f)) for f in key_fields]
            key_pred = " ".join(part for part in key_pred_parts if part).lower()

            if not key_gt and not key_pred:
                score = 1.0
            elif not key_gt or not key_pred:
                score = 0.0
            else:
                score = fuzz.ratio(key_gt, key_pred) / 100.0

            candidates.append((score, i, j))

    candidates.sort(reverse=True, key=lambda x: x[0])

    matched_gt, matched_pred = set(), set()
    matched_pairs = []

    for score, i, j in candidates:
        if score < match_threshold:
            break
        if i in matched_gt or j in matched_pred:
            continue
        matched_gt.add(i)
        matched_pred.add(j)
        matched_pairs.append((i, j, score))

    unmatched_gt = [i for i in range(len(gt_list)) if i not in matched_gt]
    unmatched_pred = [j for j in range(len(pred_list)) if j not in matched_pred]

    return matched_pairs, unmatched_gt, unmatched_pred


def list_of_dicts_score(gt_list, pred_list, key_fields, all_fields, match_threshold=0.5):
    """
    Score a list-of-dicts field (education, experience, etc.)
    Returns entry-level precision/recall/f1, plus field_accuracy averaged over matched pairs only.
    """
    if not isinstance(gt_list, list):
        gt_list = []
    if not isinstance(pred_list, list):
        pred_list = []

    if not gt_list and not pred_list:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "field_accuracy": 1.0}

    if not gt_list:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0, "field_accuracy": 0.0}

    if not pred_list:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "field_accuracy": 0.0}

    matched_pairs, unmatched_gt, unmatched_pred = match_list_entries(
        gt_list, pred_list, key_fields, match_threshold
    )

    tp = len(matched_pairs)
    precision = tp / len(pred_list)
    recall = tp / len(gt_list)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    field_scores = []
    for i, j, _ in matched_pairs:
        gt_item = gt_list[i] if i < len(gt_list) else {}
        pred_item = pred_list[j] if j < len(pred_list) else {}
        s = object_similarity(gt_item, pred_item, all_fields)
        if s is not None:
            field_scores.append(s)

    field_accuracy = sum(field_scores) / len(field_scores) if field_scores else None

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "field_accuracy": field_accuracy
    }


def count_field_score(gt_counts, pred_counts):
    """Score flat numeric dict fields (e.g. publication_summary): 1 - normalized absolute error, averaged."""
    if not isinstance(gt_counts, dict) or not gt_counts:
        return None
    if not isinstance(pred_counts, dict):
        pred_counts = {}

    scores = []
    for key in gt_counts:
        gt_v = _to_num(gt_counts.get(key, 0))
        pred_v = _to_num(pred_counts.get(key, 0))
        denom = max(gt_v, pred_v, 1)
        scores.append(max(0.0, 1.0 - abs(gt_v - pred_v) / denom))

    return sum(scores) / len(scores) if scores else None