
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from redactor import PIIRedactor
from test_corpus import TEST_CASES


def locate_ground_truth(text, gt_pairs):
    spans = []
    for substring, label in gt_pairs:
        idx = text.find(substring)
        if idx == -1:
            raise ValueError(f"GT substring not found in text: {substring!r}")
        spans.append((idx, idx + len(substring), label))
    return spans


def overlap_ratio(a_start, a_end, b_start, b_end):
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union else 0.0


def evaluate():
    redactor = PIIRedactor()

    categories = ["PERSON", "ORG", "EMAIL", "PHONE", "ADDRESS", "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS"]
    tp = {c: 0 for c in categories}
    fp = {c: 0 for c in categories}
    fn = {c: 0 for c in categories}

    total_chars = 0
    correct_chars = 0

    false_positive_examples = []
    false_negative_examples = []

    for text, gt_pairs in TEST_CASES:
        gt_spans = locate_ground_truth(text, gt_pairs)
        detected = redactor.detect(text)

        gt_matched = [False] * len(gt_spans)
        det_matched = [False] * len(detected)

        for gi, (gs, ge, glabel) in enumerate(gt_spans):
            for di, d in enumerate(detected):
                if det_matched[di]:
                    continue
                if d.label != glabel:
                    continue
                if overlap_ratio(gs, ge, d.start, d.end) >= 0.5:
                    gt_matched[gi] = True
                    det_matched[di] = True
                    tp[glabel] += 1
                    break

        for gi, matched in enumerate(gt_matched):
            if not matched:
                gs, ge, glabel = gt_spans[gi]
                fn[glabel] += 1
                false_negative_examples.append((text[gs:ge], glabel))

        for di, matched in enumerate(det_matched):
            if not matched:
                d = detected[di]
                fp[d.label] += 1
                false_positive_examples.append((d.text, d.label))

        gt_mask = [False] * len(text)
        for gs, ge, _ in gt_spans:
            for i in range(gs, ge):
                gt_mask[i] = True
        det_mask = [False] * len(text)
        for d in detected:
            for i in range(d.start, d.end):
                det_mask[i] = True

        total_chars += len(text)
        correct_chars += sum(1 for a, b in zip(gt_mask, det_mask) if a == b)

    return tp, fp, fn, total_chars, correct_chars, false_positive_examples, false_negative_examples


def main():
    tp, fp, fn, total_chars, correct_chars, fp_examples, fn_examples = evaluate()

    categories = ["PERSON", "ORG", "EMAIL", "PHONE", "ADDRESS", "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS"]

    print(f"{'Category':<14}{'TP':>4}{'FP':>4}{'FN':>4}{'Precision':>12}{'Recall':>10}{'F1':>8}")
    print("-" * 62)

    overall_tp = overall_fp = overall_fn = 0
    rows = []
    for c in categories:
        t, f, n = tp[c], fp[c], fn[c]
        overall_tp += t
        overall_fp += f
        overall_fn += n
        precision = t / (t + f) if (t + f) else float("nan")
        recall = t / (t + n) if (t + n) else float("nan")
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) and precision == precision and recall == recall and (precision + recall) > 0
              else float("nan"))
        rows.append((c, t, f, n, precision, recall, f1))
        p_str = f"{precision:.2f}" if precision == precision else "n/a"
        r_str = f"{recall:.2f}" if recall == recall else "n/a"
        f1_str = f"{f1:.2f}" if f1 == f1 else "n/a"
        print(f"{c:<14}{t:>4}{f:>4}{n:>4}{p_str:>12}{r_str:>10}{f1_str:>8}")

    overall_precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) else float("nan")
    overall_recall = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) else float("nan")
    overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall)
                  if (overall_precision + overall_recall) else float("nan"))
    char_accuracy = correct_chars / total_chars if total_chars else float("nan")

    print("-" * 62)
    print(f"{'OVERALL':<14}{overall_tp:>4}{overall_fp:>4}{overall_fn:>4}"
          f"{overall_precision:>12.2f}{overall_recall:>10.2f}{overall_f1:>8.2f}")
    print(f"\nCharacter-level accuracy: {char_accuracy:.4f} "
          f"({correct_chars}/{total_chars} characters correctly labeled PII/non-PII)")

    if fp_examples:
        print("\nFalse positives (flagged but not real PII):")
        for text_, label in fp_examples:
            print(f"  [{label}] {text_!r}")

    if fn_examples:
        print("\nFalse negatives (missed PII):")
        for text_, label in fn_examples:
            print(f"  [{label}] {text_!r}")

    return rows, overall_precision, overall_recall, overall_f1, char_accuracy, fp_examples, fn_examples


if __name__ == "__main__":
    main()
