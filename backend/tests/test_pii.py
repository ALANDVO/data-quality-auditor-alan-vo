import pytest
from app.services.pii_scanner import PIIScanner

def test_pii_scanner_detects_emails():
    scanner = PIIScanner()
    records = [
        {"user_id": str(i), "contact": f"user{i}@corp.example.com"}
        for i in range(10)
    ]
    findings = scanner.scan_columns(records)
    assert any(f.column == "contact" and "email" in f.types for f in findings)
    email_f = next(f for f in findings if f.column == "contact")
    assert email_f.sensitivity == "high"

def test_pii_scanner_column_name_hints():
    scanner = PIIScanner()
    records = [
        {"user_ssn": "encrypted_blob", "customer_name": "Entity 42"}
        for _ in range(5)
    ]
    findings = scanner.scan_columns(records)
    columns_flagged = [f.column for f in findings]
    assert "user_ssn" in columns_flagged
    assert "customer_name" in columns_flagged

def test_pii_scanner_clean_data():
    scanner = PIIScanner()
    records = [
        {"metric_id": i, "latency_ms": 12.5 * i, "status": "200"}
        for i in range(10)
    ]
    findings = scanner.scan_columns(records)
    assert len(findings) == 0

def test_pii_scanner_column_hint_email_only():
    """Column named with email hint but non-email values should still be high sensitivity."""
    scanner = PIIScanner()
    records = [{"user_id": "1", "contact_email": "user_001"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    email_f = next(f for f in findings if f.column == "contact_email")
    assert email_f.sensitivity == "high"
    assert "email" in email_f.types
    assert "GDPR" in email_f.regulation
    assert "mask_email" in email_f.recommended_mask

def test_pii_scanner_column_hint_phone_only():
    """Column named with phone hint but non-phone values should be medium sensitivity."""
    scanner = PIIScanner()
    records = [{"phone_number": "N/A"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    phone_f = next(f for f in findings if f.column == "phone_number")
    assert phone_f.sensitivity == "medium"
    assert "phone" in phone_f.types
    assert "TCPA" in phone_f.regulation
    assert "mask_phone" in phone_f.recommended_mask

def test_pii_scanner_column_hint_ip_address_only():
    """Column named with IP hint but non-IP values should be medium sensitivity."""
    scanner = PIIScanner()
    records = [{"client_ip": "unknown"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    ip_f = next(f for f in findings if f.column == "client_ip")
    assert ip_f.sensitivity == "medium"
    assert "ip_address" in ip_f.types
    assert "Online Identifier" in ip_f.regulation
    assert "truncate_ip" in ip_f.recommended_mask

def test_pii_scanner_column_hint_date_of_birth_only():
    """Column named with DOB hint but non-date values should be medium sensitivity."""
    scanner = PIIScanner()
    records = [{"birth_date": "redacted"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    dob_f = next(f for f in findings if f.column == "birth_date")
    assert dob_f.sensitivity == "medium"
    assert "date_of_birth" in dob_f.types
    assert "HIPAA" in dob_f.regulation
    assert "generalize_dob" in dob_f.recommended_mask

def test_pii_scanner_sensitivity_not_downgraded_by_lower_priority_match():
    """When high and medium sensitivity patterns both match, highest wins and first mask is preserved."""
    scanner = PIIScanner()
    # Credit card number also matches phone pattern (16 digits)
    records = [{"payment_card": "4111111111111111"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    f = next(f for f in findings if f.column == "payment_card")
    assert "credit_card" in f.types
    assert "phone" in f.types
    assert f.sensitivity == "high"
    assert "mask_card" in f.recommended_mask

def test_pii_scanner_mask_rule_preserved_when_hint_matches_pattern():
    """When pattern detection and column hint both apply, pattern mask_rule is preserved."""
    scanner = PIIScanner()
    records = [{"contact_email": "user1@corp.example.com"} for _ in range(10)]
    findings = scanner.scan_columns(records)
    f = next(f for f in findings if f.column == "contact_email")
    assert "email" in f.types
    assert f.sensitivity == "high"
    assert "mask_email" in f.recommended_mask
