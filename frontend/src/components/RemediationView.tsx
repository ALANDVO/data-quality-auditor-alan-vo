import React, { useState } from 'react';
import { RemediationPlaybookResponse } from '../api/client';

interface RemediationViewProps {
  playbook: RemediationPlaybookResponse | null;
  onDownloadScript: () => Promise<void>;
}

export const RemediationView: React.FC<RemediationViewProps> = ({
  playbook,
  onDownloadScript,
}) => {
  const [copied, setCopied] = useState(false);

  if (!playbook) {
    return (
      <div className="empty-state">
        <p>No remediation playbook generated yet. Run an audit on a dataset first to generate code transforms.</p>
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(playbook.full_script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="remediation-view">
      <div className="section-header">
        <div>
          <h2>Remediation Engine: {playbook.dataset_name}</h2>
          <p className="section-desc">Automated, reproducible data cleaning transforms derived from audit findings</p>
        </div>
        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={handleCopy}>
            {copied ? 'Copied to Clipboard!' : 'Copy Python Code'}
          </button>
          <button className="btn btn-primary" onClick={onDownloadScript}>
            Download clean_pipeline.py
          </button>
        </div>
      </div>

      <div className="remediation-rules-section">
        <h3>Generated Cleaning Transforms ({playbook.rules.length})</h3>
        <div className="rules-grid">
          {playbook.rules.map((rule, idx) => (
            <div key={idx} className="rule-card">
              <div className="rule-card-header">
                <div>
                  <span className={`badge badge-sens-${rule.severity}`}>{rule.severity.toUpperCase()}</span>
                  <span className="rule-issue-type"> {rule.issue_type.replace('_', ' ').toUpperCase()}</span>
                </div>
                <span className="rule-col">Target: <code>{rule.target_column}</code></span>
              </div>
              <p className="rule-desc">{rule.rule_description}</p>
              <pre className="code-block">
                <code>{rule.python_snippet}</code>
              </pre>
            </div>
          ))}

          {playbook.rules.length === 0 && (
            <p className="empty-text">No defects detected in this dataset. Zero remediation actions required.</p>
          )}
        </div>
      </div>

      <div className="full-script-section">
        <h3>Complete Executable Pipeline</h3>
        <pre className="code-block full-script">
          <code>{playbook.full_script}</code>
        </pre>
      </div>

      {playbook.advisory_notes && (
        <div className="advisory-notes-box">
          <strong>Advisory Note:</strong> {playbook.advisory_notes}
        </div>
      )}
    </div>
  );
};
