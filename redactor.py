
import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

import spacy
from faker import Faker


@dataclass
class Span:
    start: int
    end: int
    text: str
    label: str
    priority: int


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

CC_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}(?!\d)"
)

DOB_CONTEXT_RE = re.compile(
    r"(?i)\b(?:date of birth|d\.?o\.?b\.?|born on|born in)\b"
    r"(?:\s+(?:is|was|of))?\s*[:\-]?\s*"
    r"(?P<date>\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4})"
)

ADDRESS_KEYWORDS = re.compile(
    r"(?i)\b(village|taluka|road|street|marg|nagar|floor|building|society|"
    r"complex|block|lane|colony|apartment|sector|plot no\.?|farms|wing|"
    r"industrial estate|industrial park|chs|midc|estate|off)\b"
)
INDIA_PIN_RE = re.compile(r"\b\d{3}\s?\d{3}\b")
US_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")

ORG_DENYLIST = {
    "sebi", "bse", "nse", "roc", "icai", "rbi", "scrr", "scra", "asba", "upi",
    "companies act", "sebi act", "sebi icdr regulations", "depositories act",
    "income tax act", "fema", "the companies act", "sebi icdr", "icdr",
    "stock exchanges", "board of directors", "our board", "our company",
    "qibs", "niis", "riis", "bidders", "designated stock exchange",
    "scores", "gsm", "asm", "stt", "npci",
    "ip", "ssn", "dob", "pin", "cc", "id",
    "social security number", "social security", "credit card", "ssn number",
}

PERSON_DENYLIST = {
    "offer", "company", "board", "bidder", "bidders", "trust", "fund",
    "group", "corporation", "committee", "issuer", "allotment", "prospectus",
    "expiry", "pre-offer", "post-offer", "directors", "auditors",
    "shareholders", "promoters", "trustees", "operations", "syndicate",
    "bid", "neft", "rtgs", "imps", "mutual funds", "mutual fund",
    "listing", "bhavan", "cap price", "selling shareholder", "corrigenda",
    "widely circulated marathi daily newspaper", "showroom",
    "brlm", "challan", "villa", "email", "bill", "key managerial personnel",
    "reference rate", "registered broker", "share transfer agents",
    "wilful defaulter", "pat margin", "shareholder",
}

ORG_JARGON_WORDS = {
    "regulations", "regulation", "report", "reports", "statement",
    "statements", "form", "forms", "standards", "standard", "committee",
    "authority", "framework", "policy", "policies", "circular", "circulars",
    "facility", "account", "accounts", "monetary fund", "reporting",
    "act", "rules", "rule", "code", "scheme", "schemes", "portion",
    "period", "date", "price", "shares", "share", "issue",
    "board", "bids", "bid", "operations", "syndicate", "directors",
    "fraud", "personnel", "investors", "auditors", "shareholders",
    "shareholder", "promoters", "prospectus", "company", "offer",
    "mutual funds", "mutual fund", "locations", "instrument",
    "designated", "allotment", "certifications", "certification",
    "capital employed", "diluted eps", "working days", "equity",
    "underwriters", "underwriter",
    "upi id", "scsbs", "expenditure",
    "pipeline", "cap price", "eps", "npa", "asba bidders", "bidder(s",
    "selling shareholder", "cin", "allottees", "financial information",
    "first bidder", "risks", "non-resident", "ind as", "group companies",
    "extra budgetary resources", "independent director", "fraudulent",
    "venture capital fund", "working capital days", "registrar",
    "directorate general", "ddugjy", "definitions", "abbreviations",
    "market data", "forward-looking statements", "risk factors",
    "promoter group", "promoter", "inter alia", "cts no", "moa",
    "indian rupees", "pradhan mantri", "national electricity plan",
    "upi bidders", "quick service restaurants",
}

ORG_EXACT_ONLY_DENY = {
    "private limited", "bank limited", "floor", "tower",
    "corporate office", "registered office", "united states dollars",
    "capital work", "5th floor", "bank facilities",
    "long term bank facilities", "national monetization pipeline",
    "upi bidder(s", "depositories", "depository",
}

KNOWN_PLACE_NAMES = {
    "maharashtra", "pune", "mumbai", "chakan", "baner", "khed", "kanjurmarg",
    "taloja", "raigad", "ahilyanagar", "ahmednagar", "india", "panvel",
    "birdewadi", "supa", "bandra", "vikhroli", "mahim",
}

CIN_RE = re.compile(r"^[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")
ORG_LEADING_STOPWORDS = {"the", "a", "an", "our", "its", "this", "that", "such"}


def luhn_check(digits: str) -> bool:
    digits = [int(d) for d in digits]
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class FakeMapper:

    def __init__(self, seed: int = 42):
        self.faker = Faker()
        Faker.seed(seed)
        self._map: Dict[str, str] = {}

    def _key(self, label: str, text: str) -> str:
        return f"{label}:{re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()}"

    def _match_case(self, original: str, fake: str) -> str:
        if original.isupper():
            return fake.upper()
        if original.istitle():
            return fake.title()
        return fake

    def get(self, label: str, text: str) -> str:
        key = self._key(label, text)
        if key in self._map:
            fake = self._map[key]
        else:
            fake = self._generate(label, text)
            self._map[key] = fake
        if label in ("PERSON", "ORG"):
            return self._match_case(text, fake)
        return fake

    def _generate(self, label: str, text: str) -> str:
        f = self.faker
        if label == "EMAIL":
            return f.safe_email()
        if label == "PHONE":
            if text.strip().startswith("+"):
                return "+91 " + f.msisdn()[3:12]
            return f.phone_number()
        if label == "SSN":
            return f.ssn()
        if label == "CREDIT_CARD":
            return f.credit_card_number()
        if label == "IP_ADDRESS":
            return f.ipv4_public()
        if label == "DOB":
            return f.date_of_birth().strftime("%B %d, %Y")
        if label == "ADDRESS":
            return f.address().replace("\n", ", ")
        if label == "PERSON":
            return f.name()
        if label == "ORG":
            return f.company()
        return "[REDACTED]"

    def export(self) -> Dict[str, str]:
        return dict(self._map)


class PIIRedactor:
    PRIORITY = {
        "EMAIL": 0,
        "IP_ADDRESS": 1,
        "SSN": 2,
        "CREDIT_CARD": 3,
        "PHONE": 4,
        "DOB": 5,
        "ADDRESS": 6,
        "PERSON": 7,
        "ORG": 8,
    }

    def __init__(self, seed: int = 42, spacy_model: str = "en_core_web_sm"):
        self.mapper = FakeMapper(seed=seed)
        self.nlp = spacy.load(spacy_model, disable=["lemmatizer", "tagger", "parser"])
        self.audit_log: List[dict] = []


    def _find_structured(self, text: str) -> List[Span]:
        spans: List[Span] = []

        for m in EMAIL_RE.finditer(text):
            spans.append(Span(m.start(), m.end(), m.group(), "EMAIL", self.PRIORITY["EMAIL"]))

        for m in IPV4_RE.finditer(text):
            spans.append(Span(m.start(), m.end(), m.group(), "IP_ADDRESS", self.PRIORITY["IP_ADDRESS"]))

        for m in SSN_RE.finditer(text):
            spans.append(Span(m.start(), m.end(), m.group(), "SSN", self.PRIORITY["SSN"]))

        for m in CC_CANDIDATE_RE.finditer(text):
            raw_digits = re.sub(r"[ -]", "", m.group())
            if 13 <= len(raw_digits) <= 19 and luhn_check(raw_digits):
                spans.append(Span(m.start(), m.end(), m.group(), "CREDIT_CARD", self.PRIORITY["CREDIT_CARD"]))

        for m in DOB_CONTEXT_RE.finditer(text):
            g = m.group("date")
            start = m.start("date")
            end = m.end("date")
            spans.append(Span(start, end, g, "DOB", self.PRIORITY["DOB"]))

        for m in PHONE_RE.finditer(text):
            digit_count = len(re.sub(r"\D", "", m.group()))
            if not (8 <= digit_count <= 13):
                continue
            candidate = m.group()
            has_plus = candidate.strip().startswith("+")
            window_start = max(0, m.start() - 25)
            context = text[window_start : m.start()]
            has_keyword = bool(re.search(r"(?i)\b(tel|telephone|phone|mobile|contact|fax|call|office)\b", context))
            looks_like_year_range = bool(re.fullmatch(r"(19|20)\d{2}[\s\-]+(19|20)\d{2}", candidate.strip()))
            if looks_like_year_range:
                continue
            if not (has_plus or has_keyword):
                continue
            spans.append(Span(m.start(), m.end(), m.group(), "PHONE", self.PRIORITY["PHONE"]))

        delim_re = re.compile(r"[:;\n]|\.\s|\bat\b|\blocated\b|\boffice\b|\bfacility\b")
        for kw in ADDRESS_KEYWORDS.finditer(text):
            window_start = max(0, kw.start() - 100)
            left_window = text[window_start : kw.start()]
            delims = list(delim_re.finditer(left_window))
            left_bound = (window_start + delims[-1].end()) if delims else window_start

            window_end = min(len(text), kw.end() + 150)
            right_window = text[kw.end() : window_end]
            pin_m = INDIA_PIN_RE.search(right_window) or US_ZIP_RE.search(right_window)
            if not pin_m:
                continue
            tail = right_window[pin_m.end() :]
            stop = re.search(r"[.\n;]", tail)
            tail_end = pin_m.end() + (stop.start() if stop else min(40, len(tail)))
            right_bound = kw.end() + tail_end

            raw_chunk = text[left_bound:right_bound]
            stripped = raw_chunk.strip(" ,")
            if stripped:
                offset = raw_chunk.find(stripped)
                new_start = left_bound + offset
                new_end = new_start + len(stripped)
                spans.append(Span(new_start, new_end, stripped, "ADDRESS", self.PRIORITY["ADDRESS"]))

        return spans

    def _find_ner(self, text: str) -> List[Span]:
        spans: List[Span] = []
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                norm = ent.text.lower().strip()
                if norm in PERSON_DENYLIST:
                    continue
                if any(re.search(rf"\b{re.escape(w)}\b", norm) for w in PERSON_DENYLIST):
                    continue
                if re.search(r"\d", ent.text):
                    continue
                if ADDRESS_KEYWORDS.search(ent.text):
                    continue
                if norm in KNOWN_PLACE_NAMES or any(tok in KNOWN_PLACE_NAMES for tok in norm.split()):
                    continue
                spans.append(Span(ent.start_char, ent.end_char, ent.text, "PERSON", self.PRIORITY["PERSON"]))
            elif ent.label_ == "ORG":
                norm = ent.text.lower().strip()
                if norm in ORG_DENYLIST:
                    continue
                if norm in ORG_EXACT_ONLY_DENY:
                    continue
                if len(norm) <= 4 and ent.text.isupper():
                    continue
                if any(re.search(rf"\b{re.escape(w)}\b", norm) for w in ORG_JARGON_WORDS):
                    continue
                first_word = norm.split(" ", 1)[0] if norm else ""
                if first_word in ORG_LEADING_STOPWORDS:
                    continue
                if norm in KNOWN_PLACE_NAMES or any(tok in KNOWN_PLACE_NAMES for tok in norm.split()):
                    continue
                if CIN_RE.match(ent.text.strip()):
                    continue
                spans.append(Span(ent.start_char, ent.end_char, ent.text, "ORG", self.PRIORITY["ORG"]))
        return spans

    def _resolve_overlaps(self, spans: List[Span]) -> List[Span]:
        spans_sorted = sorted(spans, key=lambda s: (s.priority, s.start))
        accepted: List[Span] = []
        occupied: List[Tuple[int, int]] = []

        def overlaps(a, b):
            return not (a[1] <= b[0] or b[1] <= a[0])

        for s in spans_sorted:
            if any(overlaps((s.start, s.end), occ) for occ in occupied):
                continue
            accepted.append(s)
            occupied.append((s.start, s.end))

        return sorted(accepted, key=lambda s: s.start)

    def detect(self, text: str) -> List[Span]:
        spans = self._find_structured(text) + self._find_ner(text)
        return self._resolve_overlaps(spans)


    def redact_text(self, text: str) -> str:
        if not text or not text.strip():
            return text
        spans = self.detect(text)
        if not spans:
            return text

        out = text
        for s in sorted(spans, key=lambda s: s.start, reverse=True):
            fake = self.mapper.get(s.label, s.text)
            out = out[: s.start] + fake + out[s.end :]
            self.audit_log.append(
                {"type": s.label, "original": s.text, "replacement": fake}
            )
        return out

    def get_mapping(self) -> Dict[str, str]:
        return self.mapper.export()

    def get_audit_log(self) -> List[dict]:
        return self.audit_log
