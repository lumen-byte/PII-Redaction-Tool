# Evaluation Report

## Methodology

Two complementary evaluations were run, because the real deliverable
document has no ground-truth PII annotations and, being a genuine public
regulatory filing, naturally contains zero instances of 4 of the 8
required categories (SSN, credit card, DOB, IP address).

### 1. Synthetic labeled test set (`eval/test_corpus.py` + `eval/run_eval.py`)

An 18-case, hand-labeled corpus covering all 8 PII types plus 6 "hard
negative" distractors (order/ticket numbers, CIN/ISIN codes, statutory
acronyms like SEBI/BSE/NSE, a non-birth date, a Luhn-failing digit
string, and a bare 6-digit number with no address context) — mirroring
the assignment's own guidance that "Order"/"Ticket" numbers should not
be swept up as PII.

Detected spans are matched against ground truth by **label + ≥50% span
overlap**; unmatched ground truth = false negative, unmatched detections
= false positive. A **character-level accuracy** is also computed
(every character in the corpus is PII/not-PII per ground truth vs. per
prediction) as the more classic "accuracy" figure.

Run with: `python3 eval/run_eval.py`

### 2. Real-document evaluation (manual spot-check + recall proxy)

Since there's no ground truth for the actual prospectus, precision was
estimated by drawing **random samples of 50 detections each** from the
PERSON and ORG categories (the two NER-based, hardest categories) and
manually judging each one as a true or false positive. Recall for the
two structured categories that *do* appear in the real document (EMAIL,
PHONE) was estimated by comparing the tool's output against an
**independent, unfiltered baseline regex** run directly over the same
extracted document text — if the tool catches everything the naive
baseline catches, that's strong evidence of high recall on this
document.

## Results — Synthetic Test Set

| Category | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| EMAIL | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PHONE | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ADDRESS | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| SSN | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| CREDIT_CARD | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DOB | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| IP_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **OVERALL** | **20** | **0** | **0** | **1.00** | **1.00** | **1.00** |

**Character-level accuracy: 95.4%** (1574/1650 characters correctly
labeled PII/non-PII). This is below the perfect span-level score because
overlap-based span matching (≥50% overlap counts as a match) tolerates
small boundary differences that character-level scoring does not — e.g.
an address span that's a few characters short of the ground-truth
boundary still counts as a full span match but loses points at the
character level.

All 6 hard-negative cases (order/ticket numbers, CIN/ISIN, SEBI/BSE/NSE,
non-birth date, Luhn-failing digit string, bare 6-digit number) produced
**zero false positives** — the tool correctly left them unredacted.

**Caveat:** this is a small, hand-curated set, and several of its
denylist entries were added specifically because they appeared as false
positives during development. A perfect score here demonstrates the tool
handles the patterns I *thought to test for* — it is not a claim of
generalization to arbitrary new documents. See the real-document results
below for a less favorable, and more representative, picture.

## Results — Real Document (Red Herring Prospectus)

Category breakdown of the final redaction run (908 total replacements):

| Category | Count |
|---|---|
| ORG | 451 |
| PERSON | 303 |
| EMAIL | 70 |
| PHONE | 49 |
| ADDRESS | 35 |
| SSN / CREDIT_CARD / DOB / IP_ADDRESS | 0 (none present in source) |

### Estimated precision (manual review of random 50-item samples)

| Category | Estimated precision | Notes |
|---|---|---|
| PERSON | **~84%** (42/50) | Main failure mode: truncated NER spans merging a name with an adjacent role word ("Ramos Shareholder", "Rajesh Branch") |
| ORG | **~60%** (30/50) | Main failure mode: Title-Case legal/financial defined terms and government scheme names that look like organization names to a generic NER model ("Corporation Finance Department Division", "National Electricity Plan") but are not companies |
| EMAIL | 100% in samples reviewed | Well-formed, low-ambiguity pattern |
| PHONE | 100% in samples reviewed | After adding a keyword/`+`-prefix context requirement to suppress fiscal-year and registration-number false positives |
| ADDRESS | 100% in samples reviewed (all 35 manually read) | All are genuine street/office addresses |

**The gap between the synthetic-corpus PERSON/ORG precision (100%) and
the real-document precision (~84% / ~60%) is the single most important
finding of this evaluation.** It reflects a real limitation of
general-purpose NER on adversarial, jargon-dense legal/financial text,
not a flaw specific to my test design — and no amount of curated-corpus
tuning fully closes that gap; a denylist only catches the patterns
someone thought to look for. In this document, the effective ORG
precision is not much better than a coin flip, which is likely
disqualifying for unattended production use.

### Estimated recall (structured categories, via independent baseline)

| Category | Baseline (naive regex) unique hits | Caught by tool | Missed |
|---|---|---|---|
| EMAIL | 26 | 40 (superset) | **0** |
| PHONE (+91-prefixed) | 14 | 33 (superset) | **0** |

The tool's unique counts exceed the naive baseline's because the tool's
phone pattern also catches non-`+91`-prefixed local formats the baseline
regex wasn't looking for. Zero misses against the baseline is a strong
(though not exhaustive) recall signal for these two categories on this
document.

A genuine, documented **recall bug was found and fixed** during this
evaluation: Indian PIN codes in the source document are frequently
written with a space in the middle ("410 501" rather than "410501"),
which the original 6-contiguous-digit regex missed entirely. Fixing this
raised ADDRESS detections in the real document from 3 to 35 — a direct,
measurable example of how spot-checking against the real deliverable
caught a gap the synthetic corpus (which I had written with contiguous
PIN codes) did not.

PERSON/ORG recall on the real document was not independently measured
(there's no practical way to hand-annotate all ~1,000 name/company
mentions across a 500-page document within the assignment's scope), but
spot checks confirmed the promoter family's name ("Kushal Hegde" and its
variants) was caught consistently across every capitalization style
(Title Case, ALL CAPS, with/without middle name) found in the document.

## Summary

| Metric | Synthetic corpus | Real document (estimated) |
|---|---|---|
| Overall precision | 1.00 | PERSON ~0.84, ORG ~0.60, structured types ~1.00 |
| Overall recall | 1.00 | EMAIL/PHONE ~1.00 (vs. baseline); PERSON/ORG not fully measurable |
| Character-level accuracy | 0.954 | N/A (no ground truth) |

The honest takeaway: **the tool is strong on structured PII (email,
phone, address, and — validated only synthetically — SSN, credit card,
DOB, IP) in both settings, and reasonably strong on person names, but
company-name detection is the weak point** when applied to real
legal/financial text, due to the inherent difficulty of distinguishing
proper organization names from capitalized legal jargon using a small,
general-purpose NER model. See `README.md` for suggested production
upgrades (Presidio with custom recognizers, or a domain-tuned NER model).
