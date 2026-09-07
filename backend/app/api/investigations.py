from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import re

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Investigation, AuditLog
from backend.app.schemas.schemas import InvestigationCreate, InvestigationResponse, InvestigationUpdate
from backend.app.services.graph_service import GraphService

router = APIRouter(prefix="/api/investigations", tags=["Investigation Workspace"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.get("", response_model=List[InvestigationResponse])
def list_investigations(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    return db.query(Investigation).order_by(Investigation.created_date.desc()).all()

@router.get("/{id}", response_model=InvestigationResponse)
def get_investigation(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {id} not found"
        )
    return inv

@router.get("/{id}/network")
def get_investigation_network(
    id: str,
    scope: str = Query("case", pattern="^(case|direct|2hop|full)$", description="Scope of the network: case, direct, 2hop, full"),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {id} not found"
        )
    return GraphService.get_investigation_network(db, id, scope=scope)

@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
    inv_in: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    # Auto-generate ID if not provided (INV-YYYY-XXX)
    inv_id = inv_in.id
    if not inv_id:
        year = datetime.utcnow().year
        count = db.query(Investigation).count() + 1
        inv_id = f"INV-{year}-{count:03d}"
    else:
        # Validate format
        if not re.match(r"^INV-\d{4}-\d{3,4}$", inv_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Investigation ID must match format INV-YYYY-XXX"
            )
        # Check uniqueness
        exists = db.query(Investigation).filter(Investigation.id == inv_id).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Investigation ID {inv_id} already exists"
            )

    db_inv = Investigation(
        id=inv_id,
        title=inv_in.title,
        description=inv_in.description,
        created_by=current_user.username,
        status=inv_in.status or "Active",
        priority=inv_in.priority or "Medium",
        entities_json=inv_in.entities_json or [],
        notes=inv_in.notes or ""
    )
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)

    # Audit logging
    log = AuditLog(
        user_id=current_user.id,
        action="create_investigation",
        resource=f"investigation:{inv_id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return db_inv

@router.put("/{id}", response_model=InvestigationResponse)
def update_investigation(
    id: str,
    inv_in: InvestigationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    db_inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not db_inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {id} not found"
        )

    # Update fields
    if inv_in.title is not None:
        db_inv.title = inv_in.title
    if inv_in.description is not None:
        db_inv.description = inv_in.description
    if inv_in.status is not None:
        db_inv.status = inv_in.status
    if inv_in.priority is not None:
        db_inv.priority = inv_in.priority
    if inv_in.entities_json is not None:
        db_inv.entities_json = inv_in.entities_json
    if inv_in.notes is not None:
        db_inv.notes = inv_in.notes

    db.commit()
    db.refresh(db_inv)

    # Audit logging
    log = AuditLog(
        user_id=current_user.id,
        action="update_investigation",
        resource=f"investigation:{id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return db_inv

@router.delete("/{id}")
def delete_investigation(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    db_inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not db_inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {id} not found"
        )

    db.delete(db_inv)
    db.commit()

    # Audit logging
    log = AuditLog(
        user_id=current_user.id,
        action="delete_investigation",
        resource=f"investigation:{id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return {"success": True, "message": f"Investigation {id} successfully deleted"}
