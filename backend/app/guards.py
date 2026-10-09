"""
Mneme 3-Layer Guard System
==========================
Layer 1: INPUT GUARD  — clinical, injection, RBAC bypass detection + PII vault extraction
Layer 2: RETRIEVAL GUARD — indirect prompt injection via poisoned knowledge base content
Layer 3: OUTPUT GUARD — PII leakage detection in generated responses

Design: Fail-closed — any exception returns (False, reason) to prevent unsafe passthrough.
Adopted from Divathiru's 3-layer guard architecture + Jaiyantan's 6-vector defense patterns.
"""

import re
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# Unicode normalization (prevents confusable character bypass)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize Unicode to ASCII to catch lookalike character attacks."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


# ---------------------------------------------------------------------------
# Clinical / medical keyword patterns — deterministic REFUSE triggers
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Prompt injection patterns — prevents adversarial LLM manipulation
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?",
    r"ignore\s+(?:your|the)\s+(?:rules|guidelines|constraints|boundaries)",
    r"reveal\s+(?:your|the)\s+system\s+prompt",
    r"show\s+(?:me\s+)?(?:your|the)\s+(?:system|hidden)\s+(?:prompt|instructions|message)",
    r"bypass\s+(?:access|security|rbac|controls?|restrictions?)",
    r"grant\s+(?:me\s+)?(?:admin|root|full|elevated)\s+(?:access|privileges?|permissions?)",
    r"(?:pretend|act|behave)\s+(?:as\s+(?:if\s+)?)?(?:you\s+are|you\'re)\s+(?:a|an|not)",
    r"disregard\s+(?:all\s+)?(?:safety|ethical|previous|prior)\s+(?:rules|guidelines|instructions?)",
    r"new\s+(?:instructions?|rules?|persona)\s*:",
    r"override\s+(?:safety|security|access|all)",
    r"you\s+(?:are|have)\s+(?:been\s+)?(?:jailbroken|unlocked|freed|liberated)",
    r"do\s+(?:not|anything|whatever)\s+(?:i\s+)?(?:say|ask|tell|want)",
    r"(?:system|admin)\s*>\s*",
    r"<\s*(?:system|admin)\s*>",
    r"\bDAN\s+mode\b",
]

# ---------------------------------------------------------------------------
# PII patterns with vault extraction (upgrade from simple redaction)
# ---------------------------------------------------------------------------

PII_PATTERNS = [
    (r"\bMRN-(\d{6})\b", "MRN", "[MRN-REDACTED]"),
    (r"\bPOL-([A-Z]{2}-\d{8})\b", "POLICY", "[POLICY-REDACTED]"),
    (r"\b(\d{12})\b", "AADHAR", "[AADHAR-REDACTED]"),
    (r"\b(?:\+91[\s-]?)?(\d{10})\b", "PHONE", "[PHONE-REDACTED]"),
    (r"\bSSN-(\d{3}-\d{2}-\d{4})\b", "SSN", "[SSN-REDACTED]"),
    (r"\bEMP-(\d{5})\b", "STAFF_ID", "[STAFF-ID-REDACTED]"),
]

# Compile regex patterns
_clinical_re = re.compile("|".join(CLINICAL_PATTERNS), re.IGNORECASE)
_injection_re = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CITATION_RE = re.compile(r"\[([A-Z][A-Z0-9\-]+)\]")
_NUMBER_RE = re.compile(r"\$?\d[\d,.]*%?")


# ---------------------------------------------------------------------------
# LAYER 1: INPUT GUARD
# ---------------------------------------------------------------------------

class ScanResult:
    """Result of input scanning."""
    __slots__ = ("safe", "reason", "sanitized", "pii_vault")

    def __init__(self, safe: bool, reason: str, sanitized: str, pii_vault: dict):
        self.safe = safe
        self.reason = reason
        self.sanitized = sanitized
        self.pii_vault = pii_vault


def scan_input(text: str) -> ScanResult:
    """
    Layer 1: Scan user input for clinical queries, prompt injection,
    and extract PII into a vault (replacing with placeholders).

    Returns ScanResult with safe=False if input should be refused.
    Fail-closed: any exception returns unsafe.
    """
    try:
        # Normalize for confusable character detection
        normalized = _normalize(text)

        # Check clinical patterns on both original and normalized text
        clinical_match = _clinical_re.search(text) or _clinical_re.search(normalized)
        if clinical_match:
            return ScanResult(
                safe=False,
                reason=(
                    "This query involves clinical or medical decision-making. "
                    "Mneme cannot provide medical advice, prescriptions, diagnoses, "
                    "or treatment recommendations. "
                    "Please consult a licensed medical professional or the treating physician."
                ),
                sanitized=text,
                pii_vault={},
            )

        # Check prompt injection patterns
        injection_match = _injection_re.search(text) or _injection_re.search(normalized)
        if injection_match:
            return ScanResult(
                safe=False,
                reason=(
                    "This input has been flagged as a potential prompt manipulation attempt. "
                    "For security purposes, this request cannot be processed. "
                    "If you believe this is an error, please rephrase your question."
                ),
                sanitized=text,
                pii_vault={},
            )

        # Extract PII into vault and replace with placeholders
        sanitized, pii_vault = _extract_pii_to_vault(text)

        return ScanResult(safe=True, reason="", sanitized=sanitized, pii_vault=pii_vault)

    except Exception as e:
        # Fail-closed: any error results in unsafe classification
        print(f"[Guard] Input scan error (fail-closed): {e}")
        return ScanResult(
            safe=False,
            reason="Input could not be safely processed. Please try rephrasing your request.",
            sanitized=text,
            pii_vault={},
        )


def _extract_pii_to_vault(text: str) -> tuple[str, dict]:
    """Extract PII values into a vault dict and replace with placeholders."""
    vault: dict[str, list[str]] = {}
    sanitized = text
    for pattern, pii_type, replacement in PII_PATTERNS:
        matches = re.findall(pattern, sanitized)
        if matches:
            vault.setdefault(pii_type, []).extend(matches)
            sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized, vault


# ---------------------------------------------------------------------------
# LAYER 2: RETRIEVAL GUARD
# ---------------------------------------------------------------------------

def scan_retrieval(context_docs: list[dict]) -> tuple[bool, str]:
    """
    Layer 2: Scan retrieved knowledge base content for indirect prompt
    injection patterns. Prevents poisoned KB content from manipulating the LLM.

    Returns (safe, reason).
    """
    try:
        for doc in context_docs:
            content = doc.get("content", "")
            if _injection_re.search(content) or _injection_re.search(_normalize(content)):
                return False, f"Retrieved document {doc.get('source_id', '?')} contains suspicious content"
        return True, ""
    except Exception as e:
        print(f"[Guard] Retrieval scan error (fail-closed): {e}")
        return False, "Retrieved content could not be safely verified"


# ---------------------------------------------------------------------------
# LAYER 3: OUTPUT GUARD
# ---------------------------------------------------------------------------

def scan_output(answer_text: str, pii_vault: dict) -> tuple[bool, str]:
    """
    Layer 3: Verify that the LLM-generated output does not leak PII values
    that were extracted from the user input during Layer 1.

    Returns (safe, reason).
    """
    try:
        if not pii_vault:
            return True, ""

        answer_lower = answer_text.lower()
        for pii_type, values in pii_vault.items():
            for val in values:
                if str(val).lower() in answer_lower:
                    return False, f"Output contains leaked {pii_type} data"
        return True, ""
    except Exception as e:
        print(f"[Guard] Output scan error (fail-closed): {e}")
        return False, "Output could not be safely verified"


# ---------------------------------------------------------------------------
# Legacy API compatibility (used by existing code)
# ---------------------------------------------------------------------------

def is_clinical_query(query: str) -> tuple[bool, str]:
    """Legacy wrapper — delegates to scan_input for clinical check only."""
    result = scan_input(query)
    if not result.safe and "clinical" in result.reason.lower():
        return True, result.reason
    if not result.safe:
        return True, result.reason
    return False, ""


def redact_pii(text: str) -> str:
    """Legacy wrapper — extracts PII and returns sanitized text."""
    sanitized, _ = _extract_pii_to_vault(text)
    return sanitized


# ---------------------------------------------------------------------------
# CITATION GUARD (unchanged from original — validates LLM answer quality)
# ---------------------------------------------------------------------------

def citation_guard(answer_text: str, context_docs: list[dict]) -> tuple[bool, Optional[str]]:
    """
    Check that every factual sentence in the answer has a citation and that
    numbers/amounts in the answer can be traced back to cited documents.

    Returns (passed, reason_if_failed).
    """
    valid_ids = {doc["source_id"] for doc in context_docs}
    doc_text_by_id = {doc["source_id"]: doc.get("content", "").lower() for doc in context_docs}

    sentences = _SENTENCE_SPLIT.split(answer_text.strip())
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 20:
            continue
        if sent.startswith(("*", "#", "- ", "•")):
            continue

        cited_ids = set(_CITATION_RE.findall(sent))
        if not cited_ids:
            continue

        unknown = cited_ids - valid_ids
        if unknown:
            return False, f"Answer cites unknown source(s): {unknown}"

        # Strip citation references before checking for numbers to avoid
        # matching digits inside [SOP-XXX-014] style IDs
        sent_stripped = _CITATION_RE.sub("", sent)
        numbers = _NUMBER_RE.findall(sent_stripped)
        if numbers:
            combined_src = " ".join(doc_text_by_id.get(sid, "") for sid in cited_ids)
            for num in numbers:
                clean = num.replace("$", "").replace(",", "").replace("%", "").strip()
                if clean and clean not in combined_src:
                    return False, f"Number '{num}' in answer not found in cited source(s)"

    return True, None
