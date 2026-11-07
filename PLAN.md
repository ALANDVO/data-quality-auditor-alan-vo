# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

cli-pydantic-deprecation

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

---

Alan Vo · [alanvo.net](https://alanvo.net)
