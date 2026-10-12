import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuditScorecardView } from '../components/AuditScorecardView';
import { AuditRunResponse } from '../api/client';

const mockAuditRun: AuditRunResponse = {
  id: 'test-audit-1234',
  dataset_id: 'ds-100',
  dataset_name: 'Telemetry Dataset',
  overall_score: 0.92,
  grade: 'A',
  completeness_score: 0.95,
  consistency_score: 1.0,
  anomaly_score: 0.88,
  pii_score: 0.85,
  drift_score: 1.0,
  scorecard: {
    overall_score: 0.92,
    grade: 'A',
    dimensions: [
      { dimension: 'completeness', score: 0.95, weight: 0.3 },
      { dimension: 'consistency', score: 1.0, weight: 0.25 },
      { dimension: 'anomalies', score: 0.88, weight: 0.25 },
      { dimension: 'pii', score: 0.85, weight: 0.2 },
    ],
    record_count: 50,
    column_count: 4,
    columns: ['id', 'latency_ms', 'email', 'status'],
    completeness: [
      { column: 'id', completeness_rate: 1.0, missing_count: 0, null_rate: 0.0 },
      { column: 'latency_ms', completeness_rate: 0.9, missing_count: 5, null_rate: 0.1 },
    ],
    duplicates_count: 0,
    consistency_score: 1.0,
    anomalies: [
      { column: 'latency_ms', mean: 45.2, pstdev: 12.1, outlier_count: 2, sample_outliers: [850.0, 920.0] },
    ],
    pii_findings: [
      {
        column: 'email',
        types: ['email'],
        sensitivity: 'high',
        regulation: 'GDPR / CCPA',
        sample_evidence: 'adm***om',
        recommended_mask: 'mask_email',
      },
    ],
    deterministic_remediations: [
      'Clip 3-sigma outliers in numeric feature latency_ms',
      'Mask sensitive PII column email',
    ],
    llm_remediation_advisory: 'Prioritize column latency_ms clipping before model training.',
  },
  created_at: new Date().toISOString(),
  created_by: 'analyst',
};

describe('AuditScorecardView', () => {
  it('renders empty state when no audit run is provided', () => {
    render(<AuditScorecardView auditRun={null} onExportMarkdown={vi.fn()} />);
    expect(screen.getByText(/No audit selected/i)).toBeInTheDocument();
  });

  it('renders scorecard metrics, grade letter, and findings', () => {
    render(<AuditScorecardView auditRun={mockAuditRun} onExportMarkdown={vi.fn()} />);
    expect(screen.getByText('Audit Scorecard: Telemetry Dataset')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('92.0%')).toBeInTheDocument();
    expect(screen.getByText('Statistical Outliers (3-Sigma Deviations)')).toBeInTheDocument();
    expect(screen.getByText('Sensitive PII Leaks Detected')).toBeInTheDocument();
    expect(screen.getByText('Prioritize column latency_ms clipping before model training.')).toBeInTheDocument();
  });
});
