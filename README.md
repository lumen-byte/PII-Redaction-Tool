# PII Redaction Tool

A tool that finds personally identifiable information in a `.docx` document and swaps it for realistic fake data, while keeping a consistent mapping so that the same real entity always turns into the same fake one, wherever it appears in the document.

## Contents

- `redactor.py` - the detection and redaction engine (`PIIRedactor` class)
- `redact_docx.py` - command-line script that applies the redactor to a `.docx` file
- `eval/test_corpus.py` - a hand-labeled synthetic test set covering all eight PII types plus hard negatives
- `eval/run_eval.py` - computes precision, recall, F1, and accuracy against the test corpus
- `redacted_output.docx` - the redacted deliverable
- `audit_log.json` - a record of every original-to-fake replacement made during the real run
- `audit_log_mapping.json` - the deduplicated original-to-fake entity mapping

To run it yourself:

```bash
python redact_docx.py input.docx output_redacted.docx audit_log.json
python eval/run_eval.py
```

## Why a hybrid approach

I split the eight required PII types into two groups rather than reaching for one technique to handle everything.

**Structured PII is handled with regex.** Email addresses, phone numbers, SSNs, credit card numbers, IP addresses, and dates of birth all follow a predictable shape, so a well-designed pattern beats a slower and less precise ML model here. A few details worth calling out:

- Credit card numbers are checked against a Luhn checksum, so a random 16-digit tracking number isn't flagged just because it happens to be the right length.
- Date-of-birth detection only fires near an explicit birth-context keyword, such as "date of birth," "DOB," or "born on." Without that anchor, a document full of other dates - incorporation dates, filing dates, and so on - would produce far too many false positives.
- Address detection is a keyword-plus-postal-code heuristic. A line or sentence containing an address keyword (Village, Road, Society, Floor, Wing, and similar terms) alongside a six-digit Indian PIN or a five-digit US ZIP, within a bounded window, gets treated as one address span. The span is clipped at nearby delimiters so it doesn't pull in an unrelated preceding clause.

**Unstructured PII is handled with spaCy NER** (`en_core_web_sm`). Names of people and companies don't follow a fixed format - there's no regex for "this capitalized phrase is a person's name" - so I used spaCy's `PERSON` and `ORG` labels, with a layer of custom filtering on top (more on that below). Real financial and legal documents are dense with Title Case defined terms that a general-purpose NER model will happily mislabel as organizations, so the filtering matters more than the base model here.

**Fake replacement stays consistent.** Every detected span is replaced through [Faker](https://faker.readthedocs.io/), routed through a caching layer (`FakeMapper`) keyed on a normalized, case- and whitespace-insensitive form of the entity plus its type, and seeded for reproducibility. So "Rajesh Kushal Hegde," "RAJESH KUSHAL HEGDE," and "Rajesh Kushal Hegde" - three different capitalizations of the same name found in the source document - all resolve to the same fake name, with the fake's casing matched to the original's (Title Case or ALL CAPS) so the output still reads naturally.

**Overlaps are resolved by priority.** Structured regex matches always win over NER matches when spans overlap - for instance, an email address that NER mistook for part of an address. Among NER matches, addresses are resolved before names or organizations, since address spans are multi-word and would otherwise get fragmented by a name detected inside them.

## What counts as PII here

Per the assignment's own order/ticket-number example, I chose to treat the following as not PII, and left them unredacted:

- Order numbers, ticket IDs, ISINs, and CINs (Corporate Identity Numbers) - these are public registration or reference numbers, not personal data.
- Regulators and statutory bodies (SEBI, BSE, NSE, RBI, RoC, the Companies Act, and so on) - these are government or regulatory entities, not companies in the sense the assignment means by company-name PII.
- Generic legal and financial defined terms ("the Offer," "the Board," "Promoter Group," "Registered Office") - capitalized because they're contractually defined terms in this kind of document, not proper names.

I did redact the issuing company's own name (KSH International Limited) everywhere it appears, since the assignment explicitly lists company names as in scope - even though, in practice, redacting the subject company of an IPO prospectus makes the document considerably harder to read on its own. That's a deliberate, documented tradeoff. A production version of this tool would likely expose a flag to exclude the "home" company from redaction.

## Known limitations

This is the section I want to be most honest about. Numbers behind these claims are in `EVALUATION_REPORT.md`.

**Organization detection is the weakest category** - roughly 55-60% precision on the real document, against 100% on the synthetic test set. A real IPO prospectus is genuinely adversarial for generic NER: it's full of Title Case phrases ("Registrar of Companies," "Fraudulent Borrower," "Extra Budgetary Resources") that look like organization names to a small, general-purpose model but are actually legal jargon or defined terms. I mitigated this with an expanding denylist built from manual spot checks, but a denylist has a ceiling. A domain-tuned NER model, or something like Microsoft Presidio with custom recognizers, would do meaningfully better in production.

**Person detection is solid but not perfect** - around 85-90% precision. A handful of truncated NER spans and role-plus-name combinations, like "Lambert Shareholder" or "PAT CAGR," still slip through.

**Address detection is keyword-gated.** An address that doesn't contain one of the listed keywords (Village, Road, Society, Floor, Wing, Farms, and others) alongside a postal code simply won't be caught. One real recall bug I found and fixed during development: Indian PIN codes in this document are frequently written with a space in the middle ("410 501" rather than "410501"), which my original regex missed entirely.

**Header and table-of-contents text occasionally confuses NER.** An all-caps section title with no ordinary sentence structure produces the odd rogue false positive. I patched the specific cases I found, but it's a structural weak spot of running sentence-trained NER on non-sentence text.

**SSNs, credit card numbers, dates of birth, and IP addresses have zero real instances** in the source document, which makes sense - it's a legitimate Indian regulatory filing, and no real prospectus contains data like this. I validated these four categories entirely against the synthetic test corpus, where they scored 100% on both precision and recall. There was simply nothing to measure them against in the actual deliverable.

**Run-level formatting is collapsed.** Word frequently splits a single visible word across several internal "runs," and to reliably catch entities split this way, I redact at the whole-paragraph-text level and collapse all runs in a paragraph into the first one. That means bold, italic, and color formatting within a redacted paragraph is lost, though paragraph-level formatting (alignment, style) and table structure are preserved. A production tool would need run-boundary-aware span splicing to avoid this tradeoff.

## Adding a new PII type

Add a regex and priority entry to `PIIRedactor.PRIORITY`, plus a detection block in `_find_structured()` for structured formats, or a new `ORG`/`PERSON`-style filter block in `_find_ner()` for unstructured types spaCy can already pick out. Then add a `_generate()` branch in `FakeMapper` for the corresponding fake-value logic. The overlap resolver and audit logging need no changes - both work generically off the `Span` dataclass.
