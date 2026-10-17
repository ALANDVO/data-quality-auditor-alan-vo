# Changelog

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