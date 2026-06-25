from jiwer import cer
from rapidfuzz.distance import Levenshtein
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction


def calculate_f1(gt_text, pred_text):

    gt_tokens = set(gt_text.split())
    pred_tokens = set(pred_text.split())

    tp = len(gt_tokens & pred_tokens)

    fp = len(pred_tokens - gt_tokens)

    fn = len(gt_tokens - pred_tokens)

    precision = tp / (tp + fp) if tp + fp else 0

    recall = tp / (tp + fn) if tp + fn else 0

    if precision + recall == 0:
        return 0

    return (
        2 * precision * recall
    ) / (
        precision + recall
    )


def calculate_cer(gt_text, pred_text):

    return cer(
        gt_text,
        pred_text
    )


def calculate_ned(gt_text, pred_text):

    distance = Levenshtein.distance(
        gt_text,
        pred_text
    )

    return distance / max(
        len(gt_text),
        len(pred_text)
    )


def calculate_bleu(gt_text, pred_text):

    reference = [gt_text.split()]
    candidate = pred_text.split()

    smooth = (
        SmoothingFunction()
        .method1
    )

    return sentence_bleu(
        reference,
        candidate,
        smoothing_function=smooth
    )