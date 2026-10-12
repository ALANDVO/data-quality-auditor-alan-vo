# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to `data-quality-auditor-alan-vo` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- Modular FastAPI backend application under `backend/app` with SQLite persistence.
- Multi-dimensional data quality profiling engine (completeness, duplicates, statistical z-score anomalies, heuristic PII scanner).
- Schema and distribution drift detector comparing target datasets against baselines.
- Deterministic remediation rules generator and opt-in advisory LLM engine supporting OpenAI, Anthropic, Gemini, and Ollama.
- Keycloak OIDC bearer authentication with documented SAML brokering and environment-guarded local demo mode.
- React 18 + TypeScript + Vite frontend dashboard with interactive audit, drift, and remediation workflows.
- Comprehensive backend pytest suite and frontend vitest suite.
- Containerization setup (`compose.yaml`, backend and frontend Dockerfiles) and GitHub Actions CI workflow.
