import pytest
from app.services.auditor import DataQualityAuditor
from app.services.remediation import RemediationEngine

def test_remediation_generation_rules():
    auditor = DataQualityAuditor()
    records = [
        {"id": 1, "age": 25.0, "email": "alice@test.corp"},
        {"id": 1, "age": 25.0, "email": "alice@test.corp"},  # duplicate
        {"id": 2, "age": None, "email": "bob@test.corp"},   # missing age
        {"id": 3, "age": 999.0, "email": "carol@test.corp"}, # outlier
    ]
    # pad records to trigger statistics
    records.extend([{"id": i, "age": 30.0, "email": f"usr{i}@test.corp"} for i in range(4, 25)])

    scorecard = auditor.audit(records)
    engine = RemediationEngine()
    playbook = engine.generate_playbook("test_users", scorecard)

    assert len(playbook.rules) >= 2
    rule_types = [r.issue_type for r in playbook.rules]
    assert "duplicates" in rule_types or "missing_values" in rule_types
    assert "import pandas as pd" in playbook.full_script
    assert "def clean_dataset" in playbook.full_script
