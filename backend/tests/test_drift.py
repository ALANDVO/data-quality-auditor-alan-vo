import pytest
from app.services.drift_detector import DriftDetector

def test_drift_identical_datasets():
    detector = DriftDetector()
    records = [{"feature_a": 10.0 + i, "feature_b": 5.0} for i in range(20)]
    added, removed, common, drifts, score = detector.analyze(records, records)
    assert len(added) == 0
    assert len(removed) == 0
    assert "feature_a" in common
    assert score >= 0.99
    assert all(not d.is_drifted for d in drifts)

def test_drift_schema_changes():
    detector = DriftDetector()
    base = [{"col1": 1, "col2": 2} for _ in range(10)]
    curr = [{"col2": 2, "col3": 3} for _ in range(10)]
    added, removed, common, drifts, score = detector.analyze(curr, base)
    assert added == ["col3"]
    assert removed == ["col1"]
    assert common == ["col2"]
    assert score < 1.0

def test_drift_feature_distribution_shift():
    detector = DriftDetector()
    # Baseline mean around 10.0, current mean around 100.0 (huge distribution shift)
    base = [{"signal": 10.0 + (i % 2)} for i in range(25)]
    curr = [{"signal": 100.0 + (i % 2)} for i in range(25)]
    added, removed, common, drifts, score = detector.analyze(curr, base)
    assert len(drifts) == 1
    d = drifts[0]
    assert d.column == "signal"
    assert d.is_drifted is True
    assert d.sigma_shift > 5.0
