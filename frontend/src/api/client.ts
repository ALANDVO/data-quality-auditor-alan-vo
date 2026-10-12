export interface UserProfile {
  id: string;
  username: string;
  email?: string;
  roles: string[];
}

export interface DatasetListItem {
  id: string;
  name: string;
  filename: string;
  file_type: string;
  record_count: number;
  column_count: number;
  columns: string[];
  created_at: string;
  created_by: string;
}

export interface DatasetDetail extends DatasetListItem {
  sample_records: Record<string, any>[];
}

export interface DimensionScore {
  dimension: string;
  score: number;
  weight: number;
}

export interface ColumnCompleteness {
  column: string;
  completeness_rate: number;
  missing_count: number;
  null_rate: number;
}

export interface AnomalyDetail {
  column: string;
  mean: number;
  pstdev: number;
  outlier_count: number;
  sample_outliers: number[];
}

export interface PIIFinding {
  column: string;
  types: string[];
  sensitivity: string;
  regulation: string;
  sample_evidence?: string;
  recommended_mask: string;
}

export interface AuditScorecard {
  overall_score: number;
  grade: string;
  dimensions: DimensionScore[];
  record_count: number;
  column_count: number;
  columns: string[];
  completeness: ColumnCompleteness[];
  duplicates_count: number;
  consistency_score: number;
  anomalies: AnomalyDetail[];
  pii_findings: PIIFinding[];
  deterministic_remediations: string[];
  llm_remediation_advisory?: string;
}

export interface AuditRunResponse {
  id: string;
  dataset_id: string;
  dataset_name: string;
  overall_score: number;
  grade: string;
  completeness_score: number;
  consistency_score: number;
  anomaly_score: number;
  pii_score: number;
  drift_score: number;
  scorecard: AuditScorecard;
  created_at: string;
  created_by: string;
}

export interface FeatureDrift {
  column: string;
  baseline_mean: number;
  current_mean: number;
  sigma_shift: number;
  is_drifted: boolean;
}

export interface DriftAnalysisResponse {
  id: string;
  dataset_id: string;
  baseline_id: string;
  dataset_name: string;
  baseline_name: string;
  added_columns: string[];
  removed_columns: string[];
  common_columns: string[];
  drifts: FeatureDrift[];
  drift_score: number;
  advisory_analysis?: string;
  created_at: string;
  created_by: string;
}

export interface RemediationRule {
  target_column: string;
  issue_type: string;
  severity: string;
  rule_description: string;
  python_snippet: string;
}

export interface RemediationPlaybookResponse {
  dataset_name: string;
  rules: RemediationRule[];
  full_script: string;
  advisory_notes?: string;
}

class ApiClient {
  private baseUrl: string = '/api';
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 204) {
      return null as T;
    }

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errBody.detail || `Request failed with status ${res.status}`);
    }

    return res.json();
  }

  // Auth endpoints
  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/auth/me');
  }

  async getAuthConfig(): Promise<any> {
    return this.request('/auth/config');
  }

  async getDemoToken(role: string = 'analyst'): Promise<{ access_token: string; role: string }> {
    return this.request<{ access_token: string; role: string }>(`/auth/demo-token?role=${role}`, {
      method: 'POST',
    });
  }

  // Datasets
  async listDatasets(search?: string): Promise<{ items: DatasetListItem[]; total: number }> {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request(`/datasets${query}`);
  }

  async getDataset(id: string): Promise<DatasetDetail> {
    return this.request<DatasetDetail>(`/datasets/${id}`);
  }

  async createDataset(name: string, file_type: 'csv' | 'json', content: string): Promise<DatasetListItem> {
    return this.request<DatasetListItem>('/datasets', {
      method: 'POST',
      body: JSON.stringify({ name, file_type, content }),
    });
  }

  async deleteDataset(id: string): Promise<void> {
    return this.request<void>(`/datasets/${id}`, {
      method: 'DELETE',
    });
  }

  // Audits
  async runAudit(datasetId: string, includeLlm: boolean = false): Promise<AuditRunResponse> {
    return this.request<AuditRunResponse>('/audits', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, include_llm_advisory: includeLlm }),
    });
  }

  async listAudits(datasetId?: string): Promise<{ items: AuditRunResponse[]; total: number }> {
    const query = datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : '';
    return this.request(`/audits${query}`);
  }

  async getAudit(auditId: string): Promise<AuditRunResponse> {
    return this.request<AuditRunResponse>(`/audits/${auditId}`);
  }

  async exportAuditMarkdown(auditId: string): Promise<string> {
    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const res = await fetch(`${this.baseUrl}/audits/${auditId}/export?format=markdown`, { headers });
    if (!res.ok) throw new Error('Failed to export markdown');
    return res.text();
  }

  // Drift
  async runDrift(datasetId: string, baselineId: string, includeLlm: boolean = false): Promise<DriftAnalysisResponse> {
    return this.request<DriftAnalysisResponse>('/drift', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, baseline_id: baselineId, include_llm_advisory: includeLlm }),
    });
  }

  async listDrifts(): Promise<{ items: DriftAnalysisResponse[]; total: number }> {
    return this.request('/drift');
  }

  // Remediation
  async getPlaybook(auditId: string): Promise<RemediationPlaybookResponse> {
    return this.request<RemediationPlaybookResponse>(`/remediation/playbook/${auditId}`);
  }

  async exportScript(auditId: string): Promise<string> {
    const headers: Record<string, string> = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const res = await fetch(`${this.baseUrl}/remediation/export-script/${auditId}`, { headers });
    if (!res.ok) throw new Error('Failed to export python script');
    return res.text();
  }
}

export const api = new ApiClient();
