#!/usr/bin/env python3
"""CLI and execution entrypoint for data-quality-auditor-alan-vo.

Provides both CLI commands (audit, pii, drift) and web server launcher.
"""

import argparse
import csv
import json
import os
import sys
from typing import List, Dict, Any

# Ensure backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app.services.auditor import DataQualityAuditor
from app.services.pii_scanner import PIIScanner
from app.services.drift_detector import DriftDetector
from app.services.remediation import RemediationEngine

def load_data(path: str) -> List[Dict[str, Any]]:
    """Load tabular dataset from CSV or JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return []

    ext = os.path.splitext(path)[1].lower()
    if ext == ".json" or content.startswith(("[", "{")):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("records", "data", "rows", "results", "items"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
        except Exception:
            pass

    try:
        import io
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    except Exception:
        pass

    raise ValueError(f"Unsupported file format: {ext} (supported: .csv, .json)")

def cmd_audit(args):
    """Run full quality audit and output scorecard."""
    records = load_data(args.file)
    n = len(records)
    if not n:
        print("No records found in dataset.")
        return

    auditor = DataQualityAuditor()
    scorecard = auditor.audit(records)

    print(f"\nAudited {scorecard.record_count} records x {scorecard.column_count} columns")
    print(f"{'='*60}\nQUALITY SCORECARD\n{'='*60}")
    print(f"  {'Dimension':<18} {'Score':>10} {'Weight':>8}")
    print(f"  {'-'*40}")
    for dim in scorecard.dimensions:
        print(f"  {dim.dimension.capitalize():<18} {dim.score*100:>9.1f}% {dim.weight*100:>7.0f}%")
    print(f"\n  OVERALL QUALITY: {scorecard.overall_score*100:.1f}%   GRADE: {scorecard.grade}\n")

    print(f"{'='*60}\nFINDINGS SUMMARY\n{'='*60}")
    print(f"  Full-row duplicates: {scorecard.duplicates_count}")
    print(f"  Columns with missing values: {sum(1 for c in scorecard.completeness if c.missing_count > 0)}")
    print(f"  Statistical anomaly columns: {len(scorecard.anomalies)}")
    print(f"  PII sensitive columns: {len(scorecard.pii_findings)}")

    print(f"\n{'='*60}\nREMEDIATION RECOMMENDATIONS\n{'='*60}")
    for fix in scorecard.deterministic_remediations:
        print(f"  * {fix}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(scorecard.dict(), f, indent=2)
        print(f"\nScorecard exported to {args.output}")

def cmd_pii(args):
    """Run deep PII scan on dataset."""
    records = load_data(args.file)
    scanner = PIIScanner()
    findings = scanner.scan_columns(records)

    print(f"\nPII Scan Report for {len(records)} records:\n{'='*60}")
    if not findings:
        print("  No sensitive PII patterns detected.")
    else:
        for f in findings:
            print(f"  [!] Column '{f.column}' ({f.sensitivity.upper()} sensitivity)")
            print(f"      Entity Types: {', '.join(f.types)}")
            print(f"      Regulations:  {f.regulation}")
            print(f"      Masking Rule: {f.recommended_mask}")
            if f.sample_evidence:
                print(f"      Evidence:     {f.sample_evidence}")
            print()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([f.dict() for f in findings], f, indent=2)
        print(f"PII report saved to {args.output}")

def cmd_drift(args):
    """Run schema and distribution drift comparison."""
    cur_records = load_data(args.file)
    base_records = load_data(args.baseline)

    detector = DriftDetector()
    added, removed, common, drifts, score = detector.analyze(cur_records, base_records)

    print(f"\nDataset Drift Analysis vs Baseline\n{'='*60}")
    print(f"  Added Columns:   {sorted(added) if added else 'None'}")
    print(f"  Removed Columns: {sorted(removed) if removed else 'None'}")
    print(f"  Common Columns:  {len(common)}")
    print(f"  Drift Stability Score: {score*100:.1f}%\n")

    if drifts:
        print("  Distribution Shifts in Features:")
        for d in drifts:
            flag = "[!]" if d.is_drifted else "   "
            print(f"  {flag} {d.column:<20} base_mean={d.baseline_mean:.2f} cur_mean={d.current_mean:.2f} (shift={d.sigma_shift:.2f}σ)")
    else:
        print("  No numeric distribution shifts detected.")

    if args.output:
        out_data = {
            "added_columns": added,
            "removed_columns": removed,
            "drifts": [d.dict() for d in drifts],
            "drift_score": score,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"\nDrift report saved to {args.output}")

def cmd_serve(args):
    """Start FastAPI server."""
    import uvicorn
    from app.core.config import settings
    uvicorn.run("app.main:app", host=args.host or settings.HOST, port=args.port or settings.PORT, reload=args.reload)

def main():
    parser = argparse.ArgumentParser(
        prog="data-quality-auditor",
        description="AI data quality auditor profiling tabular datasets for completeness, anomalies, PII, and drift.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # audit command
    p_audit = sub.add_parser("audit", help="Run full data quality audit")
    p_audit.add_argument("--file", required=True, help="Path to CSV or JSON dataset")
    p_audit.add_argument("--schema", default=None, help="Optional schema baseline")
    p_audit.add_argument("--output", default=None, help="Save report to JSON file")
    p_audit.set_defaults(fn=cmd_audit)

    # pii command
    p_pii = sub.add_parser("pii", help="Run sensitive PII scanner")
    p_pii.add_argument("--file", required=True, help="Path to CSV or JSON dataset")
    p_pii.add_argument("--output", default=None, help="Save PII report to JSON file")
    p_pii.set_defaults(fn=cmd_pii)

    # drift command
    p_drift = sub.add_parser("drift", help="Detect schema and distribution drift")
    p_drift.add_argument("--file", required=True, help="Current dataset path")
    p_drift.add_argument("--baseline", required=True, help="Baseline dataset path")
    p_drift.add_argument("--output", default=None, help="Save drift report to JSON file")
    p_drift.set_defaults(fn=cmd_drift)

    # serve command
    p_serve = sub.add_parser("serve", help="Start FastAPI web backend")
    p_serve.add_argument("--host", default="127.0.0.1", help="Bind host")
    p_serve.add_argument("--port", type=int, default=8000, help="Bind port")
    p_serve.add_argument("--reload", action="store_true", help="Enable reload")
    p_serve.set_defaults(fn=cmd_serve)

    args = parser.parse_args()
    args.fn(args)

if __name__ == "__main__":
    main()
