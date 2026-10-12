import React, { useState } from 'react';
import { DatasetListItem, DatasetDetail } from '../api/client';

interface DatasetManagerProps {
  datasets: DatasetListItem[];
  selectedDataset: DatasetListItem | null;
  onSelectDataset: (d: DatasetListItem) => void;
  onCreateDataset: (name: string, type: 'csv' | 'json', content: string) => Promise<void>;
  onDeleteDataset: (id: string) => Promise<void>;
  datasetDetail: DatasetDetail | null;
  onRunAudit: (id: string, includeLlm: boolean) => Promise<void>;
  userRole: string;
}

const TEMPLATES = {
  clean: {
    name: 'Synthetic Housing Features (Clean)',
    type: 'csv' as const,
    content: `sqft,bedrooms,bathrooms,price_k,zip_code
1200,3,2,350.0,94102
1500,3,2,420.0,94103
2100,4,3,610.0,94107
1800,3,2.5,520.0,94105
1400,2,2,390.0,94102
1650,3,2,475.0,94109`,
  },
  noisy: {
    name: 'Customer Telemetry (With Outliers & PII)',
    type: 'csv' as const,
    content: `customer_id,contact_email,session_latency_ms,error_rate,signup_date
c-101,sarah.connor@sky.net,42.5,0.01,2024-01-15
c-102,john.reese@fbi.gov,,0.00,2024-01-18
c-103,harold.finch@mit.edu,48.1,0.02,2024-02-01
c-104,sameen.shaw@isa.mil,8500.0,0.50,2024-02-10
c-101,sarah.connor@sky.net,42.5,0.01,2024-01-15
c-105,root@machine.ai,null,0.00,2024-03-01`,
  },
  json_baseline: {
    name: 'Model Inference Baseline (JSON)',
    type: 'json' as const,
    content: JSON.stringify([
      { model_version: "v1.0", latency_ms: 22.4, confidence: 0.94, memory_mb: 512 },
      { model_version: "v1.0", latency_ms: 24.1, confidence: 0.92, memory_mb: 515 },
      { model_version: "v1.0", latency_ms: 21.9, confidence: 0.95, memory_mb: 510 },
      { model_version: "v1.0", latency_ms: 23.5, confidence: 0.91, memory_mb: 518 },
      { model_version: "v1.0", latency_ms: 25.0, confidence: 0.93, memory_mb: 520 }
    ], null, 2),
  }
};

export const DatasetManager: React.FC<DatasetManagerProps> = ({
  datasets,
  selectedDataset,
  onSelectDataset,
  onCreateDataset,
  onDeleteDataset,
  datasetDetail,
  onRunAudit,
  userRole,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [fileType, setFileType] = useState<'csv' | 'json'>('csv');
  const [content, setContent] = useState('');
  const [includeLlm, setIncludeLlm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [search, setSearch] = useState('');

  const handleApplyTemplate = (key: keyof typeof TEMPLATES) => {
    const t = TEMPLATES[key];
    setName(t.name);
    setFileType(t.type);
    setContent(t.content);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !content) return;
    setIsSubmitting(true);
    try {
      await onCreateDataset(name, fileType, content);
      setShowCreateModal(false);
      setName('');
      setContent('');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filtered = datasets.filter(d => d.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="dataset-manager">
      <div className="section-header">
        <div>
          <h2>Managed Datasets</h2>
          <p className="section-desc">Upload tabular data files to profile quality metrics and detect anomalies</p>
        </div>
        <div className="action-buttons">
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
            disabled={userRole === 'viewer'}
          >
            + Ingest New Dataset
          </button>
        </div>
      </div>

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search datasets..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field"
        />
      </div>

      <div className="dataset-grid">
        {filtered.map((d) => (
          <div
            key={d.id}
            className={`dataset-card ${selectedDataset?.id === d.id ? 'selected' : ''}`}
            onClick={() => onSelectDataset(d)}
          >
            <div className="dataset-header">
              <span className="file-badge">{d.file_type.toUpperCase()}</span>
              {userRole === 'admin' && (
                <button
                  className="btn-icon-danger"
                  title="Delete dataset"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete dataset '${d.name}'?`)) {
                      onDeleteDataset(d.id);
                    }
                  }}
                >
                  ✕
                </button>
              )}
            </div>
            <h3 className="dataset-title">{d.name}</h3>
            <div className="dataset-meta">
              <span>{d.record_count} rows</span>
              <span>•</span>
              <span>{d.column_count} cols</span>
            </div>
            <div className="columns-preview">
              {d.columns.slice(0, 4).map((col) => (
                <span key={col} className="col-pill">{col}</span>
              ))}
              {d.columns.length > 4 && <span className="col-pill">+{d.columns.length - 4} more</span>}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="empty-state">
            <p>No datasets found. Click "+ Ingest New Dataset" to get started.</p>
          </div>
        )}
      </div>

      {selectedDataset && (
        <div className="selected-dataset-panel">
          <div className="panel-header">
            <div>
              <h3>Active Dataset: {selectedDataset.name}</h3>
              <p className="meta-text">{selectedDataset.record_count} rows × {selectedDataset.column_count} columns • Ingested by {selectedDataset.created_by}</p>
            </div>
            <div className="audit-controls">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={includeLlm}
                  onChange={(e) => setIncludeLlm(e.target.checked)}
                />
                Opt-in Advisory LLM Insights
              </label>
              <button
                className="btn btn-success"
                onClick={() => onRunAudit(selectedDataset.id, includeLlm)}
                disabled={userRole === 'viewer'}
              >
                Run Quality Audit
              </button>
            </div>
          </div>

          {datasetDetail && datasetDetail.sample_records.length > 0 && (
            <div className="sample-records-table">
              <h4>Sample Records (First 5)</h4>
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      {datasetDetail.columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {datasetDetail.sample_records.slice(0, 5).map((row, idx) => (
                      <tr key={idx}>
                        {datasetDetail.columns.map((c) => (
                          <td key={c}>{row[c] !== null && row[c] !== undefined ? String(row[c]) : <em className="null-val">null</em>}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Ingest Tabular Dataset</h3>
            <p className="modal-sub">Paste CSV or JSON dataset or choose a preset template</p>

            <div className="template-pills">
              <span>Presets: </span>
              <button type="button" className="btn-chip" onClick={() => handleApplyTemplate('clean')}>Housing (Clean)</button>
              <button type="button" className="btn-chip" onClick={() => handleApplyTemplate('noisy')}>Telemetry (Noisy + PII)</button>
              <button type="button" className="btn-chip" onClick={() => handleApplyTemplate('json_baseline')}>Inference Baseline (JSON)</button>
            </div>

            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Dataset Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field"
                  placeholder="e.g. Sales Q3 Training Features"
                />
              </div>

              <div className="form-group">
                <label>Format</label>
                <select
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value as 'csv' | 'json')}
                  className="input-field"
                >
                  <option value="csv">CSV (Comma-Separated)</option>
                  <option value="json">JSON (Array of Records)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Data Payload</label>
                <textarea
                  required
                  rows={8}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="input-field code-input"
                  placeholder="Paste CSV rows with headers or JSON array..."
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? 'Ingesting...' : 'Ingest Dataset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
