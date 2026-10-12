import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_viewer, require_analyst
from app.models.entities import Dataset, AuditRun, AuditLog
from app.models.schemas import (
    AuditRunRequest,
    AuditRunResponse,
    AuditListResponse,
    AuditScorecard,
    UserProfile,
)
from app.services.auditor import DataQualityAuditor
from app.services.llm_service import LLMService

router = APIRouter(prefix="/audits", tags=["Audits"])

@router.post("", response_model=AuditRunResponse, status_code=status.HTTP_201_CREATED)
async def run_audit(
    payload: AuditRunRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_analyst),
):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = json.loads(dataset.data_json) if dataset.data_json else []
    auditor = DataQualityAuditor()
    scorecard = auditor.audit(records)

    # Optional advisory LLM generation
    if payload.include_llm_advisory:
        llm = LLMService()
        try:
            advisory = await llm.generate_remediation_advisory(scorecard.dict())
            scorecard.llm_remediation_advisory = advisory
        except Exception as exc:
            scorecard.llm_remediation_advisory = f"LLM advisory unavailable: {exc}"

    audit_id = str(uuid.uuid4())
    dim_dict = {d.dimension: d.score for d in scorecard.dimensions}

    audit_run = AuditRun(
        id=audit_id,
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        overall_score=scorecard.overall_score,
        grade=scorecard.grade,
        completeness_score=dim_dict.get("completeness", 0.0),
        consistency_score=dim_dict.get("consistency", 0.0),
        anomaly_score=dim_dict.get("anomalies", 0.0),
        pii_score=dim_dict.get("pii", 0.0),
        drift_score=1.0,
        summary_json=json.dumps({
            "record_count": scorecard.record_count,
            "column_count": scorecard.column_count,
            "duplicates": scorecard.duplicates_count,
            "anomalies_count": len(scorecard.anomalies),
            "pii_count": len(scorecard.pii_findings),
        }),
        details_json=json.dumps(scorecard.dict()),
        remediation_plan=json.dumps(scorecard.deterministic_remediations),
        created_by=user.username,
    )
    db.add(audit_run)

    # Audit log
    log = AuditLog(
        id=str(uuid.uuid4()),
        action="AUDIT_RUN",
        resource_type="audit_run",
        resource_id=audit_id,
        user_id=user.id,
        user_role=user.roles[0] if user.roles else "analyst",
        details_json=json.dumps({"dataset_id": dataset.id, "score": scorecard.overall_score, "grade": scorecard.grade}),
    )
    db.add(log)
    db.commit()
    db.refresh(audit_run)

    return AuditRunResponse(
        id=audit_run.id,
        dataset_id=audit_run.dataset_id,
        dataset_name=audit_run.dataset_name,
        overall_score=audit_run.overall_score,
        grade=audit_run.grade,
        completeness_score=audit_run.completeness_score,
        consistency_score=audit_run.consistency_score,
        anomaly_score=audit_run.anomaly_score,
        pii_score=audit_run.pii_score,
        drift_score=audit_run.drift_score,
        scorecard=scorecard,
        created_at=audit_run.created_at.isoformat(),
        created_by=audit_run.created_by,
    )

@router.get("", response_model=AuditListResponse)
def list_audits(
    dataset_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    query = db.query(AuditRun)
    if dataset_id:
        query = query.filter(AuditRun.dataset_id == dataset_id)

    total = query.count()
    items = query.order_by(AuditRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    response_items: List[AuditRunResponse] = []
    for a in items:
        scorecard_data = json.loads(a.details_json) if a.details_json else {}
        response_items.append(
            AuditRunResponse(
                id=a.id,
                dataset_id=a.dataset_id,
                dataset_name=a.dataset_name,
                overall_score=a.overall_score,
                grade=a.grade,
                completeness_score=a.completeness_score,
                consistency_score=a.consistency_score,
                anomaly_score=a.anomaly_score,
                pii_score=a.pii_score,
                drift_score=a.drift_score,
                scorecard=AuditScorecard(**scorecard_data) if scorecard_data else None, # type: ignore
                created_at=a.created_at.isoformat(),
                created_by=a.created_by,
            )
        )

    return AuditListResponse(items=response_items, total=total, page=page, page_size=page_size)

@router.get("/{audit_id}", response_model=AuditRunResponse)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit_run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    scorecard_data = json.loads(audit_run.details_json) if audit_run.details_json else {}
    return AuditRunResponse(
        id=audit_run.id,
        dataset_id=audit_run.dataset_id,
        dataset_name=audit_run.dataset_name,
        overall_score=audit_run.overall_score,
        grade=audit_run.grade,
        completeness_score=audit_run.completeness_score,
        consistency_score=audit_run.consistency_score,
        anomaly_score=audit_run.anomaly_score,
        pii_score=audit_run.pii_score,
        drift_score=audit_run.drift_score,
        scorecard=AuditScorecard(**scorecard_data),
        created_at=audit_run.created_at.isoformat(),
        created_by=audit_run.created_by,
    )

@router.get("/{audit_id}/export")
def export_audit(
    audit_id: str,
    format: str = Query("markdown", pattern="^(markdown|json)$"),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit_run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    scorecard_data = json.loads(audit_run.details_json) if audit_run.details_json else {}

    if format == "json":
        return Response(
            content=json.dumps(scorecard_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_{audit_id}.json"},
        )

    # Markdown export
    sc = AuditScorecard(**scorecard_data)
    md_lines = [
        f"# Data Quality Audit Report: {audit_run.dataset_name}",
        f"**Audit ID**: `{audit_run.id}`  ",
        f"**Date**: {audit_run.created_at.isoformat()}  ",
        f"**Overall Quality Score**: `{sc.overall_score * 100:.1f}%` (Grade: **{sc.grade}**)  ",
        "",
        "## Quality Dimensions Breakdown",
        "| Dimension | Score | Weight |",
        "|---|---|---|",
    ]
    for d in sc.dimensions:
        md_lines.append(f"| {d.dimension.capitalize()} | {d.score * 100:.1f}% | {d.weight * 100:.0f}% |")

    md_lines.extend([
        "",
        "## Findings Summary",
        f"- **Records Checked**: {sc.record_count}",
        f"- **Columns Checked**: {sc.column_count}",
        f"- **Full-row Duplicates**: {sc.duplicates_count}",
        f"- **Statistical Outliers Detected**: {len(sc.anomalies)}",
        f"- **Sensitive PII Columns Flagged**: {len(sc.pii_findings)}",
        "",
        "## Recommended Deterministic Remediations",
    ])
    for rem in sc.deterministic_remediations:
        md_lines.append(f"- {rem}")

    if sc.llm_remediation_advisory:
        md_lines.extend([
            "",
            "## Advisory Recommendations",
            "> " + "\n> ".join(sc.llm_remediation_advisory.splitlines()),
        ])

    return Response(
        content="\n".join(md_lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=audit_{audit_id}.md"},
    )
