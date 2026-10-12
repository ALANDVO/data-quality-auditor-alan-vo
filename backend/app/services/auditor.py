import math
import statistics
from collections import Counter
from typing import List, Dict, Any, Tuple
from app.models.schemas import (
    AuditScorecard,
    DimensionScore,
    ColumnCompleteness,
    AnomalyDetail,
    PIIFinding,
)
from app.services.pii_scanner import PIIScanner

NULL_VALUES = {None, "", "null", "NULL", "N/A", "n/a", "NA", "-", "nan", "None", "undefined"}

class DataQualityAuditor:
    """Deterministic, robust data quality auditor producing multi-dimensional scorecards."""

    def __init__(self):
        self.pii_scanner = PIIScanner()

    def audit(self, records: List[Dict[str, Any]]) -> AuditScorecard:
        n = len(records)
        if n == 0:
            return AuditScorecard(
                overall_score=0.0,
                grade="D",
                dimensions=[
                    DimensionScore(dimension="completeness", score=0.0, weight=0.30),
                    DimensionScore(dimension="consistency", score=0.0, weight=0.25),
                    DimensionScore(dimension="anomalies", score=0.0, weight=0.25),
                    DimensionScore(dimension="pii", score=0.0, weight=0.20),
                ],
                record_count=0,
                column_count=0,
                columns=[],
                completeness=[],
                duplicates_count=0,
                consistency_score=0.0,
                anomalies=[],
                pii_findings=[],
                deterministic_remediations=["Dataset contains zero records. Ingest valid data rows."],
                llm_remediation_advisory=None,
            )

        cols = list(records[0].keys())

        # 1. Completeness Profiling
        completeness_details: List[ColumnCompleteness] = []
        completeness_rates: List[float] = []
        deterministic_fixes: List[str] = []

        for col in cols:
            null_count = sum(1 for r in records if r.get(col) in NULL_VALUES)
            comp_rate = round(1.0 - (null_count / n), 4)
            null_rate = round(null_count / n, 4)
            completeness_details.append(
                ColumnCompleteness(
                    column=col,
                    completeness_rate=comp_rate,
                    missing_count=null_count,
                    null_rate=null_rate,
                )
            )
            completeness_rates.append(comp_rate)
            if null_rate > 0.05:
                deterministic_fixes.append(
                    f"Column '{col}' has {null_rate:.1%} null rate: apply median or constant imputation."
                )

        comp_score = sum(completeness_rates) / len(completeness_rates) if completeness_rates else 1.0

        # 2. Consistency & Duplicate Detection
        if n > 1:
            row_signatures = [
                tuple(sorted((str(k), str(v)) for k, v in r.items())) for r in records
            ]
            counts = Counter(row_signatures)
            duplicate_rows = sum(c - 1 for c in counts.values() if c > 1)
            consistency_score = max(0.0, 1.0 - (duplicate_rows / n))
        else:
            duplicate_rows = 0
            consistency_score = 1.0

        if duplicate_rows > 0:
            deterministic_fixes.append(
                f"Found {duplicate_rows} duplicate row(s): execute df.drop_duplicates() to deduplicate."
            )

        # 3. Statistical Anomalies on Numeric Features
        anomaly_details: List[AnomalyDetail] = []
        total_outliers = 0

        for col in cols:
            num_vals: List[float] = []
            for r in records[:5000]:
                val = r.get(col)
                if val not in NULL_VALUES:
                    try:
                        num_vals.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if len(num_vals) >= 5:
                mean_val = statistics.mean(num_vals)
                std_val = statistics.pstdev(num_vals)
                if std_val > 1e-6:
                    outliers = [v for v in num_vals if abs(v - mean_val) > 3.0 * std_val]
                    if outliers:
                        total_outliers += len(outliers)
                        anomaly_details.append(
                            AnomalyDetail(
                                column=col,
                                mean=round(mean_val, 3),
                                pstdev=round(std_val, 3),
                                outlier_count=len(outliers),
                                sample_outliers=[round(x, 2) for x in outliers[:5]],
                            )
                        )
                        lower_bound = round(mean_val - 3.0 * std_val, 2)
                        upper_bound = round(mean_val + 3.0 * std_val, 2)
                        deterministic_fixes.append(
                            f"Column '{col}' has {len(outliers)} 3-sigma outlier(s): clip values to [{lower_bound}, {upper_bound}]."
                        )

        anomaly_score = max(0.0, 1.0 - (total_outliers / max(n, 1)))

        # 4. PII Scanning
        pii_findings = self.pii_scanner.scan_columns(records)
        pii_penalty = 0.0
        for p in pii_findings:
            if p.sensitivity == "high":
                pii_penalty += 0.25
            elif p.sensitivity == "medium":
                pii_penalty += 0.12
            else:
                pii_penalty += 0.05
            deterministic_fixes.append(
                f"PII Alert on '{p.column}' ({', '.join(p.types)}): apply '{p.recommended_mask}'."
            )
        pii_score = max(0.0, 1.0 - pii_penalty)

        # 5. Composite Score Calculation
        dimensions = [
            DimensionScore(dimension="completeness", score=round(comp_score, 4), weight=0.30),
            DimensionScore(dimension="consistency", score=round(consistency_score, 4), weight=0.25),
            DimensionScore(dimension="anomalies", score=round(anomaly_score, 4), weight=0.25),
            DimensionScore(dimension="pii", score=round(pii_score, 4), weight=0.20),
        ]

        overall_score = round(
            sum(d.score * d.weight for d in dimensions), 4
        )

        if overall_score >= 0.90:
            grade = "A"
        elif overall_score >= 0.75:
            grade = "B"
        elif overall_score >= 0.60:
            grade = "C"
        else:
            grade = "D"

        if not deterministic_fixes:
            deterministic_fixes.append("Dataset passed all quality thresholds with zero critical defects.")

        return AuditScorecard(
            overall_score=overall_score,
            grade=grade,
            dimensions=dimensions,
            record_count=n,
            column_count=len(cols),
            columns=cols,
            completeness=completeness_details,
            duplicates_count=duplicate_rows,
            consistency_score=round(consistency_score, 4),
            anomalies=anomaly_details,
            pii_findings=pii_findings,
            deterministic_remediations=deterministic_fixes,
            llm_remediation_advisory=None,
        )
