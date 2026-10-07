#!/usr/bin/env python3
# data-quality-auditor — AI data quality auditor that analyzes CSV/JSON datasets for completeness, consistency, anomalies, PII leaks, and schema drift, producing a quality scorecard with LLM-generated remediation suggestions.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
def _load_data(path):
    """Load CSV or JSON into a list of dict records."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in ("records", "data", "rows", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return data
    if ext == ".csv":
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    raise ValueError(f"Unsupported format: {ext}")

def audit(args):
    """Full data quality audit with scorecard."""
    llm = LLM()
    records = _load_data(args.file)
    n = len(records)
    if not n:
        print("No records found.")
        return
    cols = list(records[0].keys())
    print(f"Auditing {n} records x {len(cols)} columns\n")

    # 1. Completeness
    print(f"{'='*60}\nCOMPLETENESS\n{'='*60}")
    completeness = {}
    for col in cols:
        nulls = sum(1 for r in records if r.get(col) in (None, "", "null", "NULL", "N/A", "n/a", "NA", "-"))
        rate = nulls / n
        completeness[col] = round(1 - rate, 4)
        flag = "⚠️ " if rate > 0.1 else "   "
        print(f"  {flag}{col:<25} complete={1-rate:.1%}  (missing: {nulls})")
    comp_score = sum(completeness.values()) / len(completeness)

    # 2. Duplicates & consistency
    print(f"\n{'='*60}\nCONSISTENCY\n{'='*60}")
    if n > 1:
        seen = Counter(tuple(sorted((str(k), str(v)) for k, v in r.items())) for r in records)
        dups = sum(c - 1 for c in seen.values() if c > 1)
        print(f"  Full-row duplicates: {dups}")
        dup_score = max(0, 1 - dups / n)
    else:
        dups, dup_score = 0, 1.0

    # 3. Statistical anomalies on numeric columns
    print(f"\n{'='*60}\nANOMALIES\n{'='*60}")
    numeric_cols = {}
    for col in cols:
        vals = []
        for r in records[:5000]:
            try: vals.append(float(r.get(col)))
            except (TypeError, ValueError): pass
        if len(vals) >= 10:
            numeric_cols[col] = vals
    anomalies_found = 0
    for col, vals in numeric_cols.items():
        mu, sigma = statistics.mean(vals), statistics.pstdev(vals) or 1.0
        outliers = [v for v in vals if abs(v - mu) > 3 * sigma]
        if outliers:
            anomalies_found += len(outliers)
            print(f"  ⚠️  {col}: {len(outliers)} outlier(s) (mean={mu:.2f}, sd={sigma:.2f}) e.g. {outliers[:3]}")
    if not numeric_cols:
        print("  No numeric columns for statistical checks.")
    anomaly_score = max(0.0, 1 - anomalies_found / max(n, 1))

    # 4. PII scan
    print(f"\n{'='*60}\nPII SCAN\n{'='*60}")
    pii_columns = []
    col_samples = {c: [str(r.get(c, ""))[:50] for r in records[:20]] for c in cols}
    pii_result = llm.generate(
        f"Dataset columns with sample values:\n{json.dumps(col_samples, indent=2)}\n\n"
        "Classify the PII sensitivity of EACH column. Respond as JSON: "
        "{\"columns\": [{\"name\": \"...\", \"type\": \"email|phone|ssn|address|name|date_of_birth|financial|location|none\", \"sensitivity\": \"high|medium|low|none\", \"regulation\": \"GDPR|CCPA|HIPAA|none\", \"sample_evidence\": \"...\"}]}",
        system="You are a data privacy officer. Identify PII based on column names AND sample values. Be conservative — when in doubt, flag it."
    )
    pii_data = _parse_json(pii_result)
    for entry in pii_data.get("columns", []):
        if entry.get("sensitivity") in ("high", "medium"):
            pii_columns.append(entry)
            print(f"  🔒 {entry['name']}: {entry.get('type','?')} [{entry.get('sensitivity','?')}] {entry.get('regulation','')}")
            if entry.get("sample_evidence"):
                print(f"       evidence: {entry['sample_evidence']}")
    if not pii_columns:
        print("  No PII detected.")
    pii_score = 1.0 - (0.4 * sum(1 for p in pii_columns if p.get("sensitivity") == "high") + 0.15 * sum(1 for p in pii_columns if p.get("sensitivity") == "medium"))

    # 5. Schema drift (if baseline provided)
    drift_score, drift_report = 1.0, []
    if args.schema:
        print(f"\n{'='*60}\nSCHEMA DRIFT\n{'='*60}")
        with open(args.schema) as f:
            baseline = json.load(f)
        base_cols = set(baseline.keys()) if isinstance(baseline, dict) else set()
        actual_cols = set(cols)
        added, removed = actual_cols - base_cols, base_cols - actual_cols
        if added: drift_report.append(f"Added columns: {sorted(added)}")
        if removed: drift_report.append(f"Removed columns: {sorted(removed)}")
        drift_score = max(0.0, 1 - len(added) / max(len(base_cols), 1) - len(removed) / max(len(base_cols), 1))
        for line in drift_report:
            print(f"  ⚠️  {line}")
        if not drift_report:
            print("  Schema matches baseline.")

    # Composite score
    weights = {"completeness": 0.30, "duplicates": 0.20, "anomalies": 0.20, "pii": 0.15, "drift": 0.15}
    scores = {"completeness": comp_score, "duplicates": dup_score, "anomalies": anomaly_score, "pii": pii_score, "drift": drift_score}
    if not args.schema:
        rest = sum(weights[k] for k in scores if k != "drift")
        scores = {k: v for k, v in scores.items() if k != "drift"}
        weights = {k: v / rest for k, v in weights.items() if k != "drift"}
    total = sum(scores[k] * weights[k] for k in scores)
    grade = "A" if total >= 0.9 else "B" if total >= 0.75 else "C" if total >= 0.6 else "D"

    print(f"\n{'='*60}\nQUALITY SCORECARD\n{'='*60}")
    print(f"  {'Dimension':<15} {'Score':>8} {'Weight':>8}")
    print(f"  {'-'*35}")
    for k in scores:
        print(f"  {k:<15} {scores[k]:>8.1%} {weights[k]:>8.1%}")
    print(f"\n  OVERALL: {total:.1%}  GRADE: {grade}")

    # LLM remediation
    print(f"\n{'='*60}\nREMEDIACTION PLAN\n{'='*60}")
    remediation = llm.generate(
        f"Data quality report for {n} records:\n"
        f"- Completeness per column: {json.dumps(completeness)}\n"
        f"- Duplicates: {dups}, Anomalies: {anomalies_found}\n"
        f"- PII columns: {json.dumps(pii_columns)}\n"
        f"- Drift: {drift_report or 'none'}\n"
        f"Columns: {cols}\n\n"
        "Generate a prioritized remediation plan. For each issue: what to fix, exact approach (regex, constraint, masking rule, pipeline step), and estimated effort (S/M/L). "
        "Order by business impact. Output as a numbered list with bold issue titles.",
        system="You are a senior data engineer. Remediation must be concrete and implementable — no 'improve data quality' hand-waving."
    )
    print(remediation)

    if args.output:
        report = {
            "file": args.file, "records": n, "columns": cols,
            "scores": scores, "overall": round(total, 4), "grade": grade,
            "completeness": completeness, "duplicates": dups, "anomalies": anomalies_found,
            "pii": pii_columns, "drift": drift_report,
            "remediation": remediation, "audited_at": datetime.now().isoformat(),
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nScorecard saved to {args.output}")
    return total

def pii(args):
    """Deep PII scan with masking recommendations."""
    llm = LLM()
    records = _load_data(args.file)
    cols = list(records[0].keys()) if records else []
    samples = {c: [str(r.get(c, ""))[:60] for r in records[:30]] for c in cols}
    print(f"PII scanning {len(records)} records, {len(cols)} columns...\n")

    result = llm.generate(
        f"Columns with sample values (first 30 records):\n{json.dumps(samples, indent=2)}\n\n"
        "For EACH column that contains PII or sensitive data, produce: "
        "{\"column\": \"...\", \"pii_types\": [\"email\", ...], \"regulation\": [\"GDPR\", ...], \"risk\": \"...\", \"masking_rule\": \"concrete regex or transform\", \"anonymization\": \"strategy\"}\n"
        "Output a JSON array. Only include columns that actually contain PII.",
        system="You are a privacy engineer. Base findings on the ACTUAL sample values, not just column names. Provide masking rules that would be copy-paste ready in Python."
    )
    findings = _parse_json_array(result)
    for f_ in findings:
        print(f"  🔒 {f_.get('column', '?')}")
        print(f"     PII types:   {', '.join(f_.get('pii_types', []))}")
        print(f"     Regulation:  {', '.join(f_.get('regulation', []))}")
        print(f"     Risk:        {f_.get('risk', '?')}")
        print(f"     Masking:     {f_.get('masking_rule', 'n/a')}")
        print()
    if not findings:
        print("  No PII detected in sampled values.")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(findings, f, indent=2)
        print(f"Saved to {args.output}")
    return findings

def drift(args):
    """Compare two datasets for schema and distribution drift."""
    llm = LLM()
    current = _load_data(args.file)
    baseline = _load_data(args.baseline)
    cur_cols = set(list(current[0].keys()) if current else [])
    base_cols = set(list(baseline[0].keys()) if baseline else [])
    print(f"Drift check: {len(current)} current vs {len(baseline)} baseline records\n")

    added, removed, common = cur_cols - base_cols, base_cols - cur_cols, cur_cols & base_cols
    print(f"  Added columns:   {sorted(added) or 'none'}")
    print(f"  Removed columns: {sorted(removed) or 'none'}")

    # Distribution drift on common numeric columns
    print(f"\n  Distribution drift (common columns):")
    drifts = []
    for col in sorted(common):
        def _nums(data):
            vals = []
            for r in data[:5000]:
                try: vals.append(float(r.get(col)))
                except (TypeError, ValueError): pass
            return vals
        cv, bv = _nums(current), _nums(baseline)
        if len(cv) >= 10 and len(bv) >= 10:
            cm, bm = statistics.mean(cv), statistics.mean(bv)
            cs, bs = statistics.pstdev(cv) or 1.0, statistics.pstdev(bv) or 1.0
            shift = abs(cm - bm) / max(bs, 1e-9)
            flag = "⚠️ " if shift > 2 else "   "
            print(f"  {flag}{col:<25} base_mean={bm:.2f} cur_mean={cm:.2f} (shift={shift:.1f}σ)")
            if shift > 2:
                drifts.append({"column": col, "baseline_mean": round(bm, 4), "current_mean": round(cm, 4), "sigma_shift": round(shift, 2)})

    if drifts:
        analysis = llm.generate(
            f"Schema changes: added={sorted(added)} removed={sorted(removed)}\n"
            f"Numeric drift: {json.dumps(drifts, indent=2)}\n\n"
            "Assess this drift: is it likely an upstream schema change, a data pipeline bug, or a legitimate business change? "
            "What should be validated before shipping? What downstream models/dashboards are at risk? Be specific.",
            system="You are a data platform engineer diagnosing drift. Distinguish real signal from noise."
        )
        print(f"\n{'='*60}\nDRIFT ANALYSIS\n{'='*60}\n{analysis}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"added": sorted(added), "removed": sorted(removed), "drifts": drifts, "checked_at": datetime.now().isoformat()}, f, indent=2)
        print(f"\nSaved to {args.output}")
    return {"added": sorted(added), "removed": sorted(removed), "drifts": drifts}

def _parse_json(raw):
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}

def _parse_json_array(raw):
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw[start:end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def main():
    import argparse
    p = argparse.ArgumentParser(prog="data-quality-auditor", description="AI data quality auditor")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="Full quality audit with scorecard")
    a.add_argument("--file", required=True); a.add_argument("--schema", default=None); a.add_argument("--output", default=None)
    a.set_defaults(fn=audit)

    pi = sub.add_parser("pii", help="Deep PII scan with masking rules")
    pi.add_argument("--file", required=True); pi.add_argument("--output", default=None)
    pi.set_defaults(fn=pii)

    d = sub.add_parser("drift", help="Schema/distribution drift vs baseline")
    d.add_argument("--file", required=True); d.add_argument("--baseline", required=True); d.add_argument("--output", default=None)
    d.set_defaults(fn=drift)

    args = p.parse_args()
    args.fn(args)

if __name__ == '__main__':
    main()
