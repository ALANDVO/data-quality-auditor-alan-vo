import React from 'react';
import { AuditRunResponse } from '../api/client';

interface AuditScorecardViewProps {
  auditRun: AuditRunResponse | null;
  onExportMarkdown: (auditId: string) => Promise<void>;
}

export const AuditScorecardView: React.FC<AuditScorecardViewProps> = ({
  auditRun,
  onExportMarkdown,
}) => {
  if (!auditRun) {
    return (
      <div className="empty-state">
        <p>No audit selected. Choose a dataset and click "Run Quality Audit" to profile dataset health.</p>
      </div>
    );
  }

  const { scorecard } = auditRun;

  return (
    <div className="scorecard-view">
      <div className="scorecard-top-bar">
        <div>
          <h2>Audit Scorecard: {auditRun.dataset_name}</h2>
          <p className="meta-text">Run ID: {auditRun.id.slice(0, 8)} • Executed {new Date(auditRun.created_at).toLocaleString()}</p>
        </div>
        <div className="action-buttons">
          <button
            className="btn btn-secondary"
            onClick={() => onExportMarkdown(auditRun.id)}
          >
            Export Markdown Report
          </button>
        </div>
      </div>

      <div className="scorecard-hero">
        <div className={`grade-badge grade-${scorecard.grade.toLowerCase()}`}>
          <span className="grade-letter">{scorecard.grade}</span>
          <span className="grade-label">Quality Grade</span>
        </div>

        <div className="overall-score-panel">
          <div className="score-number">{(scorecard.overall_score * 100).toFixed(1)}%</div>
          <div className="score-desc">Composite Dataset Quality Index</div>
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(100, scorecard.overall_score * 100)}%` }}
            />
          </div>
        </div>

        <div className="stats-metric-tiles">
          <div className="metric-tile">
            <span className="metric-val">{scorecard.record_count}</span>
            <span className="metric-lbl">Total Records</span>
          </div>
          <div className="metric-tile">
            <span className="metric-val">{scorecard.column_count}</span>
            <span className="metric-lbl">Features</span>
          </div>
          <div className="metric-tile">
            <span className="metric-val">{scorecard.duplicates_count}</span>
            <span className="metric-lbl">Duplicates</span>
          </div>
          <div className="metric-tile">
            <span className="metric-val">{scorecard.anomalies.length}</span>
            <span className="metric-lbl">Outlier Features</span>
          </div>
        </div>
      </div>

      <div className="dimensions-section">
        <h3>Quality Dimensions</h3>
        <div className="dimension-grid">
          {scorecard.dimensions.map((dim) => (
            <div key={dim.dimension} className="dimension-card">
              <div className="dim-header">
                <span className="dim-name">{dim.dimension.toUpperCase()}</span>
                <span className="dim-score">{(dim.score * 100).toFixed(1)}%</span>
              </div>
              <div className="progress-bar-bg small">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${Math.min(100, dim.score * 100)}%` }}
                />
              </div>
              <span className="dim-weight">Weight: {(dim.weight * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div className="findings-container">
        <div className="finding-block">
          <h4>Completeness Profile</h4>
          <table className="compact-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Completeness</th>
                <th>Missing Rows</th>
                <th>Null Rate</th>
              </tr>
            </thead>
            <tbody>
              {scorecard.completeness.map((c) => (
                <tr key={c.column}>
                  <td><strong>{c.column}</strong></td>
                  <td>{(c.completeness_rate * 100).toFixed(1)}%</td>
                  <td>{c.missing_count}</td>
                  <td>
                    <span className={c.null_rate > 0.1 ? 'badge badge-warning' : 'badge badge-ok'}>
                      {(c.null_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {scorecard.anomalies.length > 0 && (
          <div className="finding-block">
            <h4>Statistical Outliers (3-Sigma Deviations)</h4>
            <div className="anomalies-list">
              {scorecard.anomalies.map((a) => (
                <div key={a.column} className="anomaly-item">
                  <div className="anomaly-header">
                    <strong>{a.column}</strong>
                    <span className="badge badge-danger">{a.outlier_count} Outlier(s)</span>
                  </div>
                  <p className="anomaly-stats">Mean: {a.mean} • StdDev: {a.pstdev}</p>
                  <p className="anomaly-samples">Sample Values: {a.sample_outliers.join(', ')}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {scorecard.pii_findings.length > 0 && (
          <div className="finding-block">
            <h4>Sensitive PII Leaks Detected</h4>
            <div className="pii-list">
              {scorecard.pii_findings.map((p) => (
                <div key={p.column} className="pii-item">
                  <div className="pii-header">
                    <strong>{p.column}</strong>
                    <span className={`badge badge-sens-${p.sensitivity}`}>{p.sensitivity.toUpperCase()} SENSITIVITY</span>
                  </div>
                  <p className="pii-detail">Entity: {p.types.join(', ')} • {p.regulation}</p>
                  <p className="pii-mask">Remediation: <code>{p.recommended_mask}</code></p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="finding-block">
          <h4>Deterministic Remediations</h4>
          <ul className="remediation-list">
            {scorecard.deterministic_remediations.map((rem, idx) => (
              <li key={idx}>✓ {rem}</li>
            ))}
          </ul>
        </div>

        {scorecard.llm_remediation_advisory && (
          <div className="finding-block advisory-block">
            <h4>Advisory LLM Insights (Grounded in Verified Records)</h4>
            <div className="advisory-content">
              {scorecard.llm_remediation_advisory.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
