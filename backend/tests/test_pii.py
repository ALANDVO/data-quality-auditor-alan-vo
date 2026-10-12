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
