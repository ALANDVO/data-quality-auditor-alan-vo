# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

pii-scanner-column-hint-sensitivity

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

Status: planned

Acceptance:
- GET /api/audit-logs returns paginated audit log items with action, resource_type, user, and details
- Authenticated users can list audit log entries
- Tests cover retrieval of audit log entries

### cli-pydantic-deprecation — Replace deprecated Pydantic v2 .dict() calls with .model_dump()

Status: planned

Acceptance:
- All scorecard.dict() and entity.dict() calls replaced with .model_dump()
- No Pydantic deprecation warnings in test output

