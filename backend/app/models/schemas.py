from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = []

class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., pattern="^(csv|json)$")
    content: str  # raw CSV text or raw JSON string

class DatasetListItem(BaseModel):
    id: str
    name: str
    filename: str
    file_type: str
    record_count: int
    column_count: int
    columns: List[str]
    created_at: str
    created_by: str

class DatasetListResponse(BaseModel):
    items: List[DatasetListItem]
    total: int
    page: int
    page_size: int

class DatasetDetailResponse(DatasetListItem):
    sample_records: List[Dict[str, Any]]

class ColumnCompleteness(BaseModel):
    column: str
    completeness_rate: float
    missing_count: int
    null_rate: float

class AnomalyDetail(BaseModel):
    column: str
    mean: float
    pstdev: float
    outlier_count: int
    sample_outliers: List[float]

class PIIFinding(BaseModel):
    column: str
    types: List[str]
    sensitivity: str  # high, medium, low
    regulation: str   # GDPR, CCPA, HIPAA, etc.
    sample_evidence: Optional[str] = None
    recommended_mask: str

class DimensionScore(BaseModel):
    dimension: str
    score: float
    weight: float

class AuditScorecard(BaseModel):
    overall_score: float
    grade: str
    dimensions: List[DimensionScore]
    record_count: int
    column_count: int
    columns: List[str]
    completeness: List[ColumnCompleteness]
    duplicates_count: int
    consistency_score: float
    anomalies: List[AnomalyDetail]
    pii_findings: List[PIIFinding]
    deterministic_remediations: List[str]
    llm_remediation_advisory: Optional[str] = None

class AuditRunRequest(BaseModel):
    dataset_id: str
    include_llm_advisory: bool = False
    baseline_schema_dataset_id: Optional[str] = None

class AuditRunResponse(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    overall_score: float
    grade: str
    completeness_score: float
    consistency_score: float
    anomaly_score: float
    pii_score: float
    drift_score: float
    scorecard: AuditScorecard
    created_at: str
    created_by: str

class AuditListResponse(BaseModel):
    items: List[AuditRunResponse]
    total: int
    page: int
    page_size: int

class FeatureDrift(BaseModel):
    column: str
    baseline_mean: float
    current_mean: float
    sigma_shift: float
    is_drifted: bool

class DriftRequest(BaseModel):
    dataset_id: str
    baseline_id: str
    include_llm_advisory: bool = False

class DriftAnalysisResponse(BaseModel):
    id: str
    dataset_id: str
    baseline_id: str
    dataset_name: str
    baseline_name: str
    added_columns: List[str]
    removed_columns: List[str]
    common_columns: List[str]
    drifts: List[FeatureDrift]
    drift_score: float
    advisory_analysis: Optional[str] = None
    created_at: str
    created_by: str

class DriftListResponse(BaseModel):
    items: List[DriftAnalysisResponse]
    total: int

class RemediationRule(BaseModel):
    target_column: str
    issue_type: str
    severity: str
    rule_description: str
    python_snippet: str

class RemediationPlaybookResponse(BaseModel):
    dataset_name: str
    rules: List[RemediationRule]
    full_script: str
    advisory_notes: Optional[str] = None

class AuditLogItem(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: str
    user_id: str
    user_role: str
    details: Dict[str, Any]
    created_at: str

class AuditLogListResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
