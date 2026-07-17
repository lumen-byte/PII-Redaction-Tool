# PII Redaction Tool

Redacts personally identifiable information from a `.docx` document and
replaces it with realistic **fake** substitutes, using a consistent
mapping so the same real entity always becomes the same fake one
everywhere in the document.

## Files

| File | Purpose |
|---|---|
| `redactor.py` | Core detection + redaction engine (`PIIRedactor` class) |
| `redact_docx.py` | CLI: applies the redactor to a `.docx` file |
| `eval/test_corpus.py` | Hand-labeled synthetic test set (all 8 PII types + hard negatives) |
| `eval/run_eval.py` | Computes precision / recall / F1 / accuracy against the test corpus |
| `redacted_output.docx` | The redacted deliverable |
| `audit_log.json` | Every (original → fake) replacement made in the real run |
| `audit_log_mapping.json` | The deduplicated original→fake entity mapping |

**Run it yourself:**
```bash
python redact_docx.py input.docx output_redacted.docx audit_log.json
python eval/run_eval.py
```

## Approach: hybrid regex + NER

I did **not** use one single technique, because the eight required PII
types split naturally into two very different problems:

**1. Structured PII → regex, because it has a checkable, fixed format.**
Email, phone, SSN, credit card, IP address, and date-of-birth all have a
predictable shape. For these I wrote targeted regexes rather than
reaching for an ML model that would be slower and less precise than a
well-designed pattern:
- **Credit cards** are validated with a **Luhn checksum**, so a random
  16-digit tracking number doesn't get flagged just because it's the
  right length.
- **DOB** only fires near an explicit birth-context keyword ("date of
  birth", "DOB", "born on"/"born in") — otherwise a document with
  hundreds of *other* dates (incorporation dates, filing dates) would
  drown in false positives.
- **Address** is a keyword + postal-code heuristic: a line/sentence
  containing an address keyword (Village, Road, Society, Floor, Wing...)
  *and* a 6-digit Indian PIN or 5-digit US ZIP within a bounded window is
  treated as one address span, clipped at nearby delimiters so it doesn't
  swallow an unrelated preceding clause.

**2. Unstructured PII → spaCy NER (`en_core_web_sm`).**
Full names and company names have no fixed format — you cannot regex your
way to "this capitalized phrase is a person's name." I used spaCy's
`PERSON` and `ORG` entity labels for these, with a layer of custom filters
on top (see "Precision decisions" below), because a real financial/legal
document turns out to be full of Title-Case *defined terms* that a
generic NER model happily mislabels as organizations.

**3. Consistent fake replacement.** Every detected span is replaced using
[Faker](https://faker.readthedocs.io/), through a caching layer
(`FakeMapper`) keyed on a normalized (case/whitespace-insensitive) form of
the entity + its type, seeded for reproducibility. So "Rajesh Kushal
Hegde", "RAJESH KUSHAL HEGDE" and "Rajesh Kushal Hegde" (three different
capitalizations of the same name found in the real document) all map to
the *same* fake name, with the fake's casing matched to the original's
(Title Case / ALL CAPS) so the output still reads naturally.

**4. Overlap resolution.** Structured regex matches always win over NER
matches on overlapping text (e.g. an email inside what NER thought was an
address), and among NER matches, addresses are resolved before
names/orgs, since address spans are multi-word and would otherwise get
fragmented by a name detected inside them.

## Precision decisions (explicit, per the assignment's "Order/Ticket
number" example)

I chose to treat the following as **NOT** PII and therefore not redact them,
mirroring the assignment's own example that order/ticket numbers
shouldn't be swept up as PII by default:
- **Order numbers, ticket IDs, ISINs, CINs (Corporate Identity Numbers)** —
  these are public registration/reference numbers, not personal data.
- **Regulators and statutory bodies** (SEBI, BSE, NSE, RBI, RoC, the
  Companies Act, ...) — these are government/regulatory entities, not
  "companies" in the sense the assignment means by company-name PII.
- **Generic legal/financial defined terms** ("the Offer", "the Board",
  "Promoter Group", "Registered Office") — capitalized because they're
  contractually defined terms in this genre of document, not proper
  names.

I **did** choose to redact the issuing company's own name (KSH
International Limited) everywhere it appears, since the assignment
explicitly lists "company names" as in-scope — even though, practically,
redacting the subject company of an IPO prospectus makes the document
much harder to read standalone. This is a deliberate, documented choice;
a production version of this tool would likely expose a flag to exclude
the "home" company from redaction.

## Known limitations / false positives & negatives

This is the most important section for being honest about tradeoffs
(see `EVALUATION_REPORT.md` for the numbers behind these claims):

1. **ORG precision is the weakest category (~55-60% on the real
   document vs. 100% on my synthetic test set).** A real IPO prospectus
   is adversarial for generic NER: it's full of Title-Case capitalized
   phrases ("Registrar of Companies", "Fraudulent Borrower", "Extra
   Budgetary Resources") that *look* like organization names to a small,
   general-purpose model but are actually legal jargon or defined terms.
   I mitigated this with an expanding denylist built from manual spot
   checks, but a denylist approach has a ceiling — a domain-tuned NER
   model (or Microsoft Presidio with custom recognizers) would do
   meaningfully better in production.
2. **PERSON precision is solid (~85-90%)** but not perfect — a handful of
   truncated NER spans and role+name combinations ("Lambert
   Shareholder", "PAT CAGR") still slip through.
3. **Address detection is keyword-gated.** An address that doesn't contain
   one of the keywords in my list (Village, Road, Society, Floor, Wing,
   Farms, ...) and a postal code won't be caught. I found and fixed one
   real recall bug during development: Indian PIN codes in this document
   are frequently written with a **space in the middle** ("410 501"
   rather than "410501"), which my original regex missed entirely.
4. **Header/table-of-contents text** occasionally confuses NER (an
   all-caps section title with no normal sentence structure), producing
   the odd rogue false positive there. I patched the specific ones I
   found but this is a structural weak spot of using sentence-trained NER
   on non-sentence text.
5. **SSN / Credit Card / DOB / IP address have zero real instances** in
   the source document (it's a legitimate Indian regulatory filing, so
   this is expected — no real prospectus contains these). I validated
   these four categories entirely against the synthetic test corpus,
   where they scored 100% precision/recall; there was nothing to measure
   them against in the actual deliverable document.
6. **Run-level formatting is collapsed.** To reliably detect entities
   split across multiple Word "runs" (Word frequently splits a single
   visible word into several runs), I redact at the whole-paragraph-text
   level and collapse all runs in a paragraph into the first one. This
   means bold/italic/color formatting *within* a redacted paragraph is
   lost, though paragraph-level formatting (alignment, style) and
   table structure are preserved. A production tool would need
   run-boundary-aware span splicing to avoid this.

## Extending to a new PII type

Add a new regex + priority entry to `PIIRedactor.PRIORITY` and a
detection block in `_find_structured()` (for structured formats) or a new
`ORG`/`PERSON`-style filter block in `_find_ner()` (for unstructured
types spaCy's model can pick out), then add a `_generate()` branch in
`FakeMapper` for its fake-value logic. The overlap resolver and audit
logging need no changes — they work generically off the `Span` dataclass.
