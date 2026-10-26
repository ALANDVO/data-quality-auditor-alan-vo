from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_viewer
from app.models.entities import AuditLog
from app.models.schemas import AuditLogItem, AuditLogListResponse, UserProfile

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    """List audit log entries with pagination and optional filters."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()

    items = [
        AuditLogItem(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            user_id=log.user_id,
            user_role=log.user_role,
            details=log.details_json,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]

    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{log_id}", response_model=AuditLogItem)
def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    """Get a single audit log entry by ID."""
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return AuditLogItem(
        id=log.id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        user_id=log.user_id,
        user_role=log.user_role,
        details=log.details_json,
        created_at=log.created_at.isoformat() if log.created_at else "",
    )
