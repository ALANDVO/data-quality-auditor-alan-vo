import pytest
from app.services.auditor import DataQualityAuditor

def test_auditor_empty_dataset():
    auditor = DataQualityAuditor()
    scorecard = auditor.audit([])
    assert scorecard.record_count == 0
    assert scorecard.overall_score == 0.0
    assert scorecard.grade == "D"

def test_auditor_clean_dataset():
    auditor = DataQualityAuditor()
    records = [
        {"id": 1, "score": 85.0, "category": "A"},
        {"id": 2, "score": 90.0, "category": "B"},
        {"id": 3, "score": 88.0, "category": "A"},
        {"id": 4, "score": 92.0, "category": "C"},
        {"id": 5, "score": 87.0, "category": "B"},
    ]
    scorecard = auditor.audit(records)
    assert scorecard.record_count == 5
    assert scorecard.column_count == 3
    assert scorecard.duplicates_count == 0
    assert scorecard.consistency_score == 1.0
    assert scorecard.overall_score >= 0.85
    assert scorecard.grade in ("A", "B")

def test_auditor_missing_values_detection():
    auditor = DataQualityAuditor()
    records = [
        {"id": 1, "value": "100", "notes": "ok"},
        {"id": 2, "value": None, "notes": ""},
        {"id": 3, "value": "NULL", "notes": "n/a"},
        {"id": 4, "value": "150", "notes": None},
    ]
    scorecard = auditor.audit(records)
    assert scorecard.record_count == 4
    val_comp = next(c for c in scorecard.completeness if c.column == "value")
    assert val_comp.missing_count == 2
    assert val_comp.null_rate == 0.5
    assert val_comp.completeness_rate == 0.5

def test_auditor_duplicates_detection():
    auditor = DataQualityAuditor()
    records = [
        {"id": 1, "name": "Item A"},
        {"id": 1, "name": "Item A"},
        {"id": 1, "name": "Item A"},
        {"id": 2, "name": "Item B"},
    ]
    scorecard = auditor.audit(records)
    assert scorecard.duplicates_count == 2
    assert scorecard.consistency_score == 0.5

def test_auditor_statistical_anomalies():
    auditor = DataQualityAuditor()
    # 20 normal values around 50, plus one extreme outlier at 5000
    records = [{"val": 50.0 + (i % 3)} for i in range(25)]
    records.append({"val": 5000.0})
    scorecard = auditor.audit(records)
    assert len(scorecard.anomalies) >= 1
    anom = scorecard.anomalies[0]
    assert anom.column == "val"
    assert anom.outlier_count == 1
    assert 5000.0 in anom.sample_outliers
