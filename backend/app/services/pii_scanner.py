import re
from typing import List, Dict, Any, Optional
from app.models.schemas import PIIFinding

# Regex patterns for deterministic PII detection
PATTERNS = {
    "email": (
        re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
        "high",
        "GDPR Art. 4 / CCPA",
        "mask_email: keep first letter and domain, e.g. j***@example.com"
    ),
    "ssn": (
        re.compile(r"^\d{3}-\d{2}-\d{4}$|^\d{9}$"),
        "high",
        "HIPAA / GLBA / Privacy Act",
        "mask_ssn: redact to ***-**-XXXX"
    ),
    "credit_card": (
        re.compile(r"^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})$"),
        "high",
        "PCI-DSS / GDPR",
        "mask_card: redact to ****-****-****-XXXX"
    ),
    "phone": (
        re.compile(r"^\+?[0-9\s().-]{10,20}$"),
        "medium",
        "GDPR / CCPA / TCPA",
        "mask_phone: redact digits except last 4"
    ),
    "ip_address": (
        re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"),
        "medium",
        "GDPR Online Identifier",
        "truncate_ip: zero out last octet e.g. 192.168.1.0/24"
    ),
    "date_of_birth": (
        re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$|^\d{2}[-/]\d{2}[-/]\d{4}$"),
        "medium",
        "HIPAA 18 Identifiers",
        "generalize_dob: retain year only e.g. 1990-01-01 -> 1990"
    )
}

# Name hints in column naming
COLUMN_HINTS = {
    "email": ["email", "e_mail", "mail_address", "contact_email"],
    "ssn": ["ssn", "social_security", "social_sec", "tax_id", "sin"],
    "credit_card": ["card_num", "credit_card", "cc_num", "pan", "card_number"],
    "phone": ["phone", "telephone", "mobile", "cell", "tel_num", "phone_number"],
    "name": ["full_name", "first_name", "last_name", "surname", "customer_name", "patient_name"],
    "address": ["address", "street", "postal_code", "zip_code", "home_address"],
    "ip_address": ["ip", "ip_address", "client_ip", "remote_addr"],
    "date_of_birth": ["dob", "birth_date", "birthdate", "date_of_birth"],
}

class PIIScanner:
    """Deterministic PII scanner scanning both column metadata and value distributions."""

    def scan_columns(self, records: List[Dict[str, Any]], sample_size: int = 50) -> List[PIIFinding]:
        if not records:
            return []

        cols = list(records[0].keys())
        samples = {c: [str(r.get(c, "")) for r in records[:sample_size] if r.get(c) not in (None, "")] for c in cols}
        findings: List[PIIFinding] = []

        for col in cols:
            col_lower = col.lower()
            detected_types = set()
            highest_sens = "low"
            regulations = set()
            mask_rule = ""
            sample_evidence = None

            # 1. Pattern test on sample values
            values = samples.get(col, [])
            for p_name, (pat, sens, reg, mask) in PATTERNS.items():
                match_count = sum(1 for v in values if pat.match(v.strip()))
                if values and (match_count / len(values) >= 0.2):
                    detected_types.add(p_name)
                    if sens == "high" or highest_sens != "high":
                        highest_sens = sens
                    regulations.add(reg)
                    mask_rule = mask
                    if not sample_evidence and match_count > 0:
                        matching_val = next(v for v in values if pat.match(v.strip()))
                        # Partially redact sample in report for safety
                        sample_evidence = matching_val[:3] + "***" + matching_val[-2:] if len(matching_val) > 5 else "***"

            # 2. Column name heuristic matches
            for p_name, hints in COLUMN_HINTS.items():
                if any(hint in col_lower for hint in hints):
                    detected_types.add(p_name)
                    if p_name in ("ssn", "credit_card"):
                        highest_sens = "high"
                        regulations.add("HIPAA / PCI-DSS / GDPR")
                        mask_rule = "hash_or_tokenize: replace with irreversible SHA-256 HMAC"
                    elif p_name in ("name", "address"):
                        if highest_sens != "high":
                            highest_sens = "medium"
                        regulations.add("GDPR Art. 4 / CCPA")
                        mask_rule = "pseudonymize: replace with synthetic token"

            if detected_types:
                findings.append(
                    PIIFinding(
                        column=col,
                        types=sorted(list(detected_types)),
                        sensitivity=highest_sens,
                        regulation=", ".join(sorted(list(regulations))) or "GDPR / CCPA",
                        sample_evidence=sample_evidence,
                        recommended_mask=mask_rule or "hash_or_pseudonymize",
                    )
                )

        return findings
