import csv
import io
import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user, require_viewer, require_analyst, require_admin
from app.models.entities import Dataset, AuditLog
from app.models.schemas import (
    DatasetCreate,
    DatasetListItem,
    DatasetListResponse,
    DatasetDetailResponse,
    UserProfile,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])

def parse_dataset_content(content: str, file_type: str) -> List[Dict[str, Any]]:
    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Dataset content cannot be empty")

    if file_type == "json":
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON syntax: {err}")
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            for k in ("records", "data", "rows", "results", "items"):
                if k in parsed and isinstance(parsed[k], list):
                    return parsed[k]
            return [parsed]
        else:
            raise HTTPException(status_code=400, detail="JSON root must be an object or array of objects")

    elif file_type == "csv":
        try:
            reader = csv.DictReader(io.StringIO(content))
            rows = [dict(r) for r in reader]
            if not rows and reader.fieldnames:
                # empty file with just headers
                return []
            return rows
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid CSV structure: {err}")

    raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

@router.get("", response_model=DatasetListResponse)
def list_datasets(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    query = db.query(Dataset)
    if search:
        query = query.filter(Dataset.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.order_by(Dataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result_items: List[DatasetListItem] = []
    for d in items:
        cols = json.loads(d.columns_json) if d.columns_json else []
        result_items.append(
            DatasetListItem(
                id=d.id,
                name=d.name,
                filename=d.filename,
                file_type=d.file_type,
                record_count=d.record_count,
                column_count=d.column_count,
                columns=cols,
                created_at=d.created_at.isoformat(),
                created_by=d.created_by,
            )
        )

    return DatasetListResponse(items=result_items, total=total, page=page, page_size=page_size)

@router.post("", response_model=DatasetListItem, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_analyst),
):
    records = parse_dataset_content(payload.content, payload.file_type)
    if not records:
        raise HTTPException(status_code=400, detail="Parsed dataset contains 0 records")

    cols = list(records[0].keys())
    dataset_id = str(uuid.uuid4())
    filename = f"{payload.name.lower().replace(' ', '_')}.{payload.file_type}"

    dataset = Dataset(
        id=dataset_id,
        name=payload.name,
        filename=filename,
        file_type=payload.file_type,
        record_count=len(records),
        column_count=len(cols),
        columns_json=json.dumps(cols),
        data_json=json.dumps(records),
        created_by=user.username,
    )
    db.add(dataset)

    # Log audit event
    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        action="DATASET_INGEST",
        resource_type="dataset",
        resource_id=dataset_id,
        user_id=user.id,
        user_role=user.roles[0] if user.roles else "analyst",
        details_json=json.dumps({"name": payload.name, "records": len(records), "columns": len(cols)}),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(dataset)

    return DatasetListItem(
        id=dataset.id,
        name=dataset.name,
        filename=dataset.filename,
        file_type=dataset.file_type,
        record_count=dataset.record_count,
        column_count=dataset.column_count,
        columns=cols,
        created_at=dataset.created_at.isoformat(),
        created_by=dataset.created_by,
    )

@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_viewer),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    cols = json.loads(dataset.columns_json) if dataset.columns_json else []
    data = json.loads(dataset.data_json) if dataset.data_json else []

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        filename=dataset.filename,
        file_type=dataset.file_type,
        record_count=dataset.record_count,
        column_count=dataset.column_count,
        columns=cols,
        created_at=dataset.created_at.isoformat(),
        created_by=dataset.created_by,
        sample_records=data[:20],
    )

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_admin),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Record audit log
    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        action="DATASET_DELETE",
        resource_type="dataset",
        resource_id=dataset_id,
        user_id=user.id,
        user_role=user.roles[0] if user.roles else "admin",
        details_json=json.dumps({"name": dataset.name}),
    )
    db.add(log_entry)
    db.delete(dataset)
    db.commit()
    return None
