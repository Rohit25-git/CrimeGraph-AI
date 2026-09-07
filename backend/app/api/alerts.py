from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Alert, AuditLog
from backend.app.schemas.schemas import AlertResponse, AlertUpdate
from backend.app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/api/alerts", tags=["Investigative Alerts"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    severity: str = Query(None, description="Filter by severity (e.g. HIGH)"),
    status: str = Query(None, description="Filter by status (e.g. Requires Human Review)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status.ilike(status))
        
    return query.order_by(Alert.timestamp.desc()).all()

@router.patch("/{id}", response_model=AlertResponse)
def update_alert_status(
    id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {id} not found"
        )
        
    old_status = alert.status
    alert.status = alert_update.status
    db.commit()
    db.refresh(alert)
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="update_alert_status",
        resource=f"alert:{id}",
        result=f"STATUS_CHANGE: {old_status} -> {alert.status}",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return alert

@router.post("/retrigger-detection", status_code=status.HTTP_200_OK)
def trigger_detection(
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    """Manually re-runs all anomaly detection models."""
    count = AnomalyService.detect_all_anomalies(db)
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="retrigger_anomaly_detection",
        resource="system",
        result=f"SUCCESS: detected {count} anomalies",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"success": True, "message": f"Anomaly detection finished. Generated {count} active alerts."}
