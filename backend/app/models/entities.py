import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from app.core.database import Base

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # csv or json
    record_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    columns_json = Column(Text, default="[]")
    data_json = Column(Text, nullable=False)  # stored serialized records
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(String(128), default="system")

class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(String(36), primary_key=True, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    dataset_name = Column(String(255), nullable=False)
    overall_score = Column(Float, nullable=False)
    grade = Column(String(5), nullable=False)  # A, B, C, D
    completeness_score = Column(Float, nullable=False)
    consistency_score = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    pii_score = Column(Float, nullable=False)
    drift_score = Column(Float, default=1.0)
    summary_json = Column(Text, default="{}")
    details_json = Column(Text, default="{}")
    remediation_plan = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(String(128), default="system")

class DriftAnalysis(Base):
    __tablename__ = "drift_analyses"

    id = Column(String(36), primary_key=True, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    baseline_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    dataset_name = Column(String(255), nullable=False)
    baseline_name = Column(String(255), nullable=False)
    added_columns_json = Column(Text, default="[]")
    removed_columns_json = Column(Text, default="[]")
    common_columns_json = Column(Text, default="[]")
    drifts_json = Column(Text, default="[]")
    drift_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(String(128), default="system")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=False)
    user_id = Column(String(128), nullable=False)
    user_role = Column(String(32), nullable=False)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now, nullable=False)
