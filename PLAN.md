# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

audit-baseline-schema-drift

## Roadmap

### pii-scanner-column-hint-sensitivity — Fix PII scanner column-name hint sensitivity and metadata

Status: done

Acceptance:
- Column-name-only email detection produces high sensitivity, GDPR/CCPA regulation, and mask_email rule
- Column-name-only phone detection produces medium sensitivity with correct regulation and mask
- Column-name-only ip_address and date_of_birth detection produce medium sensitivity with correct metadata
- Sensitivity never downgrades from high to medium or medium to low when multiple PII types match a column
- mask_rule is preserved (first match wins) instead of being overwritten by later patterns

Implementation: `backend/app/services/pii_scanner.py`

Tests: `backend/tests/test_pii.py`

### audit-log-api-endpoint — Expose audit log listing API endpoint

Status: done

Acceptance:
- GET /api/audit-logs returns paginated audit log items with action, resource_type, user, and details
- Authenticated users can list audit log entries
- Tests cover retrieval of audit log entries

Implementation: `backend/app/api/audit_logs.py`

Tests: `backend/tests/test_api_integration.py`

### cli-pydantic-deprecation — Replace deprecated Pydantic v2 .dict() calls with .model_dump()

Status: done

Acceptance:
- All scorecard.dict() and entity.dict() calls replaced with .model_dump()
- No Pydantic deprecation warnings in test output

Implementation: `backend/app/api/audits.py`, `backend/app/api/drift.py`

Tests: `backend/tests/test_api_integration.py`, `backend/tests/test_drift.py`

### audit-baseline-schema-drift — Compute schema drift score when audit runs against a baseline dataset

Status: done

Acceptance:
- POST /api/audits without baseline_schema_dataset_id stores drift_score = 1.0 (unchanged behavior)
- POST /api/audits with baseline_schema_dataset_id computes schema stability score and persists it on the audit run
- Baseline dataset with a removed column produces drift_score below 1.0 in create and GET responses
- POST /api/audits with an unknown baseline_schema_dataset_id returns 404 instead of silently ignoring the field

Implementation: `backend/app/services/drift_detector.py`, `backend/app/api/audits.py`

Tests: `backend/tests/test_api_integration.py`, `backend/tests/test_drift.py`

### tighten-pii-value-patterns — Tighten PII value regexes to stop false positives

Status: planned

Acceptance:
- Phone pattern does not match values such as 192.168.1.1.5 or 2020-13-45999
- Date-of-birth pattern rejects impossible dates such as 2020-13-45
- Existing PII detection tests continue to pass

### cli-audit-schema-baseline — Honor main.py audit --schema flag for schema drift reporting

Status: planned

Acceptance:
- main.py audit --schema <file> prints schema stability score against that baseline
- Without --schema output is unchanged

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
