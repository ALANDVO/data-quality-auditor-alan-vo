import React, { useState } from 'react';
import { DatasetListItem, DriftAnalysisResponse } from '../api/client';

interface DriftViewProps {
  datasets: DatasetListItem[];
  driftResult: DriftAnalysisResponse | null;
  onRunDrift: (targetId: string, baselineId: string, includeLlm: boolean) => Promise<void>;
  userRole: string;
}

export const DriftView: React.FC<DriftViewProps> = ({
  datasets,
  driftResult,
  onRunDrift,
  userRole,
}) => {
  const [targetId, setTargetId] = useState<string>(datasets[0]?.id || '');
  const [baselineId, setBaselineId] = useState<string>(datasets[1]?.id || datasets[0]?.id || '');
  const [includeLlm, setIncludeLlm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetId || !baselineId) return;
    setIsLoading(true);
    try {
      await onRunDrift(targetId, baselineId, includeLlm);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="drift-view">
      <div className="section-header">
        <div>
          <h2>Schema & Distribution Drift Engine</h2>
          <p className="section-desc">Detect dataset column evolution and feature distribution shifts against a baseline</p>
        </div>
      </div>

      <form className="drift-selectors-card" onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group flex-1">
            <label>Target Dataset (Current)</label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="input-field"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.record_count} rows)</option>
              ))}
            </select>
          </div>

          <div className="form-group flex-1">
            <label>Reference Baseline Dataset</label>
            <select
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
              className="input-field"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.record_count} rows)</option>
              ))}
            </select>
          </div>
        </div>

        <div className="drift-form-actions">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={includeLlm}
              onChange={(e) => setIncludeLlm(e.target.checked)}
            />
            Opt-in Advisory LLM Drift Diagnosis
          </label>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading || !targetId || !baselineId || userRole === 'viewer'}
          >
            {isLoading ? 'Analyzing Drift...' : 'Compare & Analyze Drift'}
          </button>
        </div>
      </form>

      {driftResult ? (
        <div className="drift-results-panel">
          <div className="drift-metrics-hero">
            <div className="metric-tile large">
              <span className="metric-val">{(driftResult.drift_score * 100).toFixed(1)}%</span>
              <span className="metric-lbl">Overall Stability Score</span>
            </div>
            <div className="metric-tile">
              <span className="metric-val">{driftResult.added_columns.length}</span>
              <span className="metric-lbl">Added Features</span>
            </div>
            <div className="metric-tile">
              <span className="metric-val">{driftResult.removed_columns.length}</span>
              <span className="metric-lbl">Removed Features</span>
            </div>
            <div className="metric-tile">
              <span className="metric-val">
                {driftResult.drifts.filter(d => d.is_drifted).length}
              </span>
              <span className="metric-lbl">Drifted Distributions (&gt;2σ)</span>
            </div>
          </div>

          <div className="drift-breakdown-grid">
            <div className="finding-block">
              <h4>Schema Comparison</h4>
              <div className="schema-tags">
                <div className="tag-group">
                  <span className="tag-header">Added in Current:</span>
                  {driftResult.added_columns.length ? (
                    driftResult.added_columns.map(c => <span key={c} className="tag tag-added">+{c}</span>)
                  ) : <span className="empty-text">None</span>}
                </div>
                <div className="tag-group">
                  <span className="tag-header">Removed from Baseline:</span>
                  {driftResult.removed_columns.length ? (
                    driftResult.removed_columns.map(c => <span key={c} className="tag tag-removed">-{c}</span>)
                  ) : <span className="empty-text">None</span>}
                </div>
                <div className="tag-group">
                  <span className="tag-header">Common Features:</span>
                  <span className="tag tag-common">{driftResult.common_columns.length} columns aligned</span>
                </div>
              </div>
            </div>

            <div className="finding-block">
              <h4>Numeric Feature Distribution Shifts</h4>
              {driftResult.drifts.length ? (
                <table className="compact-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Baseline Mean</th>
                      <th>Current Mean</th>
                      <th>Sigma Shift</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {driftResult.drifts.map((d) => (
                      <tr key={d.column}>
                        <td><strong>{d.column}</strong></td>
                        <td>{d.baseline_mean.toFixed(2)}</td>
                        <td>{d.current_mean.toFixed(2)}</td>
                        <td>{d.sigma_shift.toFixed(2)}σ</td>
                        <td>
                          {d.is_drifted ? (
                            <span className="badge badge-danger">DRIFT DETECTED</span>
                          ) : (
                            <span className="badge badge-ok">STABLE</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-text">No numeric features available for distribution testing.</p>
              )}
            </div>
          </div>

          {driftResult.advisory_analysis && (
            <div className="finding-block advisory-block">
              <h4>Advisory Drift Assessment</h4>
              <div className="advisory-content">
                {driftResult.advisory_analysis.split('\n').map((l, i) => <p key={i}>{l}</p>)}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <p>Select two datasets above to compare schema changes and calculate statistical feature divergence.</p>
        </div>
      )}
    </div>
  );
};
