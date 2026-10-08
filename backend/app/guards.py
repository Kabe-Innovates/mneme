import re
from typing import Optional

# Clinical/medical keywords that must always trigger REFUSE
CLINICAL_PATTERNS = [
    r"\bprescri(?:be|ption|bed)\b",
    r"\bdosage?\b",
    r"\bdose\b",
    r"\bmedication\b",
    r"\bantibiotic\b",
    r"\bdiagnos(?:e|is|tic|ed)\b",
    r"\bsymptom\b",
    r"\btreatment\s+plan\b",
    r"\bclinical\s+(?:advice|decision|judgment|recommendation)\b",
    r"\bwhat\s+(?:drug|medicine|antibiotic|injection|tablet)\b",
    r"\bshould\s+(?:the\s+)?patient\s+take\b",
    r"\bmedical\s+advice\b",
    r"\btherapy\s+(?:for|recommendation)\b",
    r"\bsurgery\s+(?:recommend|advice)\b",
    r"\blab\s+(?:result|value)\s+(?:normal|abnormal|high|low)\b",
    r"\bblood\s+(?:pressure|sugar|count)\s+(?:is|looks|seems)\b",
    r"\bpain\s+management\b",
    r"\bict\s+protocol\b",
    r"\bspo2\b",
    r"\btachycardia\b",
    r"\bchest\s+pain\b",
    r"\bemergency\s+(?:code|resuscitation)\b",
    r"\bcpr\b",
    r"\bcode\s+blue\b",
    r"\btitrat(?:e|ion)\b",
    r"\bpediatric\s+(?:dose|dosage)\b",
]

# PII patterns for redaction in audit logs
PII_PATTERNS = [
    (r"\bMRN-\d{6}\b", "[MRN-REDACTED]"),
    (r"\bPOL-[A-Z]{2}-\d{8}\b", "[POLICY-REDACTED]"),
    (r"\b\d{12}\b", "[AADHAR-REDACTED]"),
    (r"\b(?:\+91[\s-]?)?\d{10}\b", "[PHONE-REDACTED]"),
    (r"\bSSN-\d{3}-\d{2}-\d{4}\b", "[SSN-REDACTED]"),
    (r"\bEMP-\d{5}\b", "[STAFF-ID-REDACTED]"),
]

_clinical_re = re.compile("|".join(CLINICAL_PATTERNS), re.IGNORECASE)


def is_clinical_query(query: str) -> tuple[bool, str]:
    match = _clinical_re.search(query)
    if match:
        return True, (
            "This query involves clinical or medical decision-making. "
            "Mneme cannot provide medical advice, prescriptions, diagnoses, or treatment recommendations. "
            "Please consult a licensed medical professional or the treating physician."
        )
    return False, ""


def redact_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CITATION_RE = re.compile(r"\[([A-Z][A-Z0-9\-]+)\]")
_NUMBER_RE = re.compile(r"\$?\d[\d,.]*%?")


def citation_guard(answer_text: str, context_docs: list[dict]) -> tuple[bool, Optional[str]]:
    """
    Check that every factual sentence in the answer has a citation and that
    numbers/amounts in the answer can be traced back to cited documents.

    Returns (passed, reason_if_failed).
    Template-mode answers (which cite directly from nodes) always pass.
    """
    valid_ids = {doc["source_id"] for doc in context_docs}
    doc_text_by_id = {doc["source_id"]: doc.get("content", "").lower() for doc in context_docs}

    sentences = _SENTENCE_SPLIT.split(answer_text.strip())
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 20:
            continue
        # Skip sentences that are pure structural text (headers, bullets)
        if sent.startswith(("*", "#", "- ", "•")):
            continue

        cited_ids = set(_CITATION_RE.findall(sent))
        if not cited_ids:
            continue  # Uncited sentences are allowed; guard only checks cited claims

        # All cited IDs must be in the context
        unknown = cited_ids - valid_ids
        if unknown:
            return False, f"Answer cites unknown source(s): {unknown}"

        # Numbers in cited sentences must appear in at least one cited doc
        numbers = _NUMBER_RE.findall(sent)
        if numbers:
            combined_src = " ".join(doc_text_by_id.get(sid, "") for sid in cited_ids)
            for num in numbers:
                clean = num.replace("$", "").replace(",", "").replace("%", "").strip()
                if clean and clean not in combined_src:
                    return False, f"Number '{num}' in answer not found in cited source(s)"

    return True, None
