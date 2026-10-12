import statistics
from typing import List, Dict, Any, Tuple
from app.models.schemas import FeatureDrift

class DriftDetector:
    """Detects schema drift and numeric feature distribution shift against a baseline."""

    def analyze(
        self,
        current_records: List[Dict[str, Any]],
        baseline_records: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[str], List[str], List[FeatureDrift], float]:
        cur_cols = set(current_records[0].keys()) if current_records else set()
        base_cols = set(baseline_records[0].keys()) if baseline_records else set()

        added = sorted(list(cur_cols - base_cols))
        removed = sorted(list(base_cols - cur_cols))
        common = sorted(list(cur_cols & base_cols))

        # Schema stability component (1.0 = identical schema)
        total_cols = max(len(base_cols), 1)
        schema_penalty = (len(added) * 0.5 + len(removed) * 0.8) / total_cols
        schema_score = max(0.0, 1.0 - schema_penalty)

        # Feature distribution drift
        feature_drifts: List[FeatureDrift] = []
        drifted_count = 0
        tested_features = 0

        for col in common:
            cur_vals = self._extract_numeric(current_records, col)
            base_vals = self._extract_numeric(baseline_records, col)

            if len(cur_vals) >= 5 and len(base_vals) >= 5:
                tested_features += 1
                base_m = statistics.mean(base_vals)
                base_s = statistics.pstdev(base_vals) or 1.0
                cur_m = statistics.mean(cur_vals)

                sigma_shift = round(abs(cur_m - base_m) / max(base_s, 1e-6), 2)
                is_drifted = sigma_shift >= 2.0
                if is_drifted:
                    drifted_count += 1

                feature_drifts.append(
                    FeatureDrift(
                        column=col,
                        baseline_mean=round(base_m, 3),
                        current_mean=round(cur_m, 3),
                        sigma_shift=sigma_shift,
                        is_drifted=is_drifted,
                    )
                )

        dist_score = (
            max(0.0, 1.0 - (drifted_count / tested_features))
            if tested_features > 0
            else 1.0
        )

        overall_drift_score = round(0.4 * schema_score + 0.6 * dist_score, 4)
        return added, removed, common, feature_drifts, overall_drift_score

    def _extract_numeric(self, records: List[Dict[str, Any]], col: str) -> List[float]:
        vals: List[float] = []
        for r in records[:5000]:
            v = r.get(col)
            if v not in (None, "", "null", "NULL", "N/A", "nan"):
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    pass
        return vals
