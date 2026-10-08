import re

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
