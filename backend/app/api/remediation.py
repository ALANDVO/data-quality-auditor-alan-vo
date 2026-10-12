import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_viewer, require_analyst
from app.models.entities import AuditRun
from app.models.schemas import (
    AuditScorecard,
    RemediationPlaybookResponse,
    UserProfile,
)
from app.services.remediation import RemediationEngine

router = APIRouter(prefix="/remediation", tags=["Remediation"])

@router.get("/playbook/{audit_id}", response_model=RemediationPlaybookResponse)
def get_playbook(
    audit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit_run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    scorecard_data = json.loads(audit_run.details_json) if audit_run.details_json else {}
    scorecard = AuditScorecard(**scorecard_data)

    engine = RemediationEngine()
    playbook = engine.generate_playbook(audit_run.dataset_name, scorecard)
    return playbook

@router.get("/export-script/{audit_id}")
def export_script(
    audit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_id).first()
    if not audit_run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    scorecard_data = json.loads(audit_run.details_json) if audit_run.details_json else {}
    scorecard = AuditScorecard(**scorecard_data)

    engine = RemediationEngine()
    playbook = engine.generate_playbook(audit_run.dataset_name, scorecard)

    return Response(
        content=playbook.full_script,
        media_type="text/x-python",
        headers={"Content-Disposition": f"attachment; filename=remediate_{audit_id[:8]}.py"},
    )
