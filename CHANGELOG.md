# Changelog

## 1.8.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.7.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.7.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed
- **Audit schema drift was ignored**: `AuditRunRequest.baseline_schema_dataset_id` was accepted by `POST /api/audits` but never read, so every audit stored a hardcoded `drift_score` of `1.0`. Supplying a baseline now computes a schema stability score from added/removed columns and persists it; omitting it keeps `drift_score` at `1.0`. An unknown baseline id now returns `404` instead of being silently ignored.
- Added `schema_stability_score()` in `backend/app/services/drift_detector.py`, reusing the same schema penalty weights as `DriftDetector.analyze` so audit-level and `/api/drift` drift scores stay consistent.

### Added
- `test_api_audit_baseline_schema_drift` in `backend/tests/test_api_integration.py` covering the no-baseline default, the with-baseline score, persistence through `GET /api/audits/{id}`, and the missing-baseline `404`.



### Tightened PII value regexes to stop false positives
- Phone pattern now rejects IP-like values (e.g., 192.168.1.1.5) and date-like values (e.g., 2020-13-45999)
- Date-of-birth pattern now validates month 01-12 and day ranges, rejecting impossible dates such as 2020-13-45
## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed
- **Pydantic v2 deprecation**: Replaced all deprecated `.dict()` calls with `.model_dump()` across the codebase (`backend/app/api/audits.py`, `backend/app/api/drift.py`, `main.py`). This eliminates Pydantic v2 deprecation warnings during test runs and CLI usage.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to `data-quality-auditor-alan-vo` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-17

### Fixed
- **PII scanner column-name hint classification**: Column-name heuristics for `email`, `phone`, `ip_address`, and `date_of_birth` types now correctly assign sensitivity levels, applicable data-protection regulations, and recommended masking rules. Previously these hint-only detections were added to the type list but left sensitivity at `low` with fallback metadata, which could undercount PII risk in the composite quality score.
- **Sensitivity non-downgrade logic**: Sensitivity escalation now uses explicit rank comparison (`{low: 1, medium: 2, high: 3}`) instead of a conditional that could downgrade a `medium` classification to `low` when a lower-priority pattern also matched. This also prevents `mask_rule` from being overwritten by a later, lower-severity pattern match.

### Added
- Six new tests in `backend/tests/test_pii.py` covering column-name-only detection for email, phone, IP address, and date-of-birth columns, plus sensitivity non-downgrade and mask-rule preservation scenarios.

## [1.0.0] - 2026-10-12 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added
- Modular FastAPI backend application under `backend/app` with SQLite persistence.
- Multi-dimensional data quality profiling engine (completeness, duplicates, statistical z-score anomalies, heuristic PII scanner).
- Schema and distribution drift detector comparing target datasets against baselines.
- Deterministic remediation rules generator and opt-in advisory LLM engine supporting OpenAI, Anthropic, Gemini, and Ollama.
- Keycloak OIDC bearer authentication with documented SAML brokering and environment-guarded local demo mode.
- React 18 + TypeScript + Vite frontend dashboard with interactive audit, drift, and remediation workflows.
- Comprehensive backend pytest suite and frontend vitest suite.
- Containerization setup (`compose.yaml`, backend and frontend Dockerfiles) and GitHub Actions CI workflow.

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
