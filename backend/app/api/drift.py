import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_viewer, require_analyst
from app.models.entities import Dataset, DriftAnalysis, AuditLog
from app.models.schemas import (
    DriftRequest,
    DriftAnalysisResponse,
    DriftListResponse,
    FeatureDrift,
    UserProfile,
)
from app.services.drift_detector import DriftDetector
from app.services.llm_service import LLMService

router = APIRouter(prefix="/drift", tags=["Drift"])

@router.post("", response_model=DriftAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def run_drift_analysis(
    payload: DriftRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_analyst),
):
    target = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    baseline = db.query(Dataset).filter(Dataset.id == payload.baseline_id).first()

    if not target or not baseline:
        raise HTTPException(status_code=404, detail="Target or baseline dataset not found")

    cur_records = json.loads(target.data_json) if target.data_json else []
    base_records = json.loads(baseline.data_json) if baseline.data_json else []

    detector = DriftDetector()
    added, removed, common, drifts, drift_score = detector.analyze(cur_records, base_records)

    advisory = None
    if payload.include_llm_advisory:
        llm = LLMService()
        try:
            drift_summary = {
                "added_columns": added,
                "removed_columns": removed,
                "drifts": [d.dict() for d in drifts],
                "drift_score": drift_score,
            }
            advisory = await llm.generate_drift_advisory(drift_summary)
        except Exception as exc:
            advisory = f"LLM drift advisory unavailable: {exc}"

    drift_id = str(uuid.uuid4())
    record = DriftAnalysis(
        id=drift_id,
        dataset_id=target.id,
        baseline_id=baseline.id,
        dataset_name=target.name,
        baseline_name=baseline.name,
        added_columns_json=json.dumps(added),
        removed_columns_json=json.dumps(removed),
        common_columns_json=json.dumps(common),
        drifts_json=json.dumps([d.dict() for d in drifts]),
        drift_score=drift_score,
        created_by=user.username,
    )
    db.add(record)

    # Log audit event
    log = AuditLog(
        id=str(uuid.uuid4()),
        action="DRIFT_ANALYSIS",
        resource_type="drift_analysis",
        resource_id=drift_id,
        user_id=user.id,
        user_role=user.roles[0] if user.roles else "analyst",
        details_json=json.dumps({"target_id": target.id, "baseline_id": baseline.id, "score": drift_score}),
    )
    db.add(log)
    db.commit()
    db.refresh(record)

    return DriftAnalysisResponse(
        id=record.id,
        dataset_id=record.dataset_id,
        baseline_id=record.baseline_id,
        dataset_name=record.dataset_name,
        baseline_name=record.baseline_name,
        added_columns=added,
        removed_columns=removed,
        common_columns=common,
        drifts=drifts,
        drift_score=drift_score,
        advisory_analysis=advisory,
        created_at=record.created_at.isoformat(),
        created_by=record.created_by,
    )

@router.get("", response_model=DriftListResponse)
def list_drifts(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    items = db.query(DriftAnalysis).order_by(DriftAnalysis.created_at.desc()).all()
    results: List[DriftAnalysisResponse] = []
    for r in items:
        results.append(
            DriftAnalysisResponse(
                id=r.id,
                dataset_id=r.dataset_id,
                baseline_id=r.baseline_id,
                dataset_name=r.dataset_name,
                baseline_name=r.baseline_name,
                added_columns=json.loads(r.added_columns_json) if r.added_columns_json else [],
                removed_columns=json.loads(r.removed_columns_json) if r.removed_columns_json else [],
                common_columns=json.loads(r.common_columns_json) if r.common_columns_json else [],
                drifts=[FeatureDrift(**d) for d in json.loads(r.drifts_json)] if r.drifts_json else [],
                drift_score=r.drift_score,
                advisory_analysis=None,
                created_at=r.created_at.isoformat(),
                created_by=r.created_by,
            )
        )
    return DriftListResponse(items=results, total=len(results))
