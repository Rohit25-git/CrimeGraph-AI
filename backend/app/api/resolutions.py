from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Entity, Relationship, EntityResolution, Evidence, Alert, AuditLog
from backend.app.schemas.schemas import EntityResolutionResponse, EntityResolutionMergeRequest
from backend.app.services.graph_service import GraphService

router = APIRouter(prefix="/api/resolutions", tags=["Entity Resolution"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.get("", response_model=List[EntityResolutionResponse])
def list_resolutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    resolutions = db.query(EntityResolution).order_by(EntityResolution.confidence.desc()).all()
    
    # Formulate custom responses with display names
    results = []
    for res in resolutions:
        src = db.query(Entity).filter(Entity.id == res.source_entity_id).first()
        tgt = db.query(Entity).filter(Entity.id == res.target_entity_id).first()
        
        results.append({
            "id": res.id,
            "source_entity_id": res.source_entity_id,
            "source_display_name": src.display_name if src else res.source_entity_id,
            "target_entity_id": res.target_entity_id,
            "target_display_name": tgt.display_name if tgt else res.target_entity_id,
            "confidence": res.confidence,
            "status": res.status,
            "created_at": res.created_at
        })
        
    return results

@router.post("/{id}")
def process_resolution(
    id: int,
    req: EntityResolutionMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    res = db.query(EntityResolution).filter(EntityResolution.id == id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resolution suggestion {id} not found"
        )
        
    if res.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolution has already been processed (status: {res.status})"
        )

    if not req.merge:
        # User rejected the merge suggestion
        res.status = "REJECTED"
        db.commit()
        
        # Log audit
        log = AuditLog(
            user_id=current_user.id,
            action="reject_merge",
            resource=f"resolution:{id}",
            result="SUCCESS",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        return {"success": True, "message": "Resolution suggestion rejected"}

    # User accepted the merge suggestion
    # We will merge Target entity (target_entity_id) INTO Source entity (source_entity_id)
    src_id = res.source_entity_id
    tgt_id = res.target_entity_id
    
    src = db.query(Entity).filter(Entity.id == src_id).first()
    tgt = db.query(Entity).filter(Entity.id == tgt_id).first()
    
    if not src or not tgt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source or Target entity no longer exists in database"
        )

    # 1. Update all Relationships pointing to target to point to source instead
    relationships_as_src = db.query(Relationship).filter(Relationship.source_entity_id == tgt_id).all()
    for rel in relationships_as_src:
        # Check if the relationship (src_id -> target) already exists
        exists = db.query(Relationship).filter(
            Relationship.source_entity_id == src_id,
            Relationship.target_entity_id == rel.target_entity_id,
            Relationship.type == rel.type
        ).first()
        if exists:
            # Delete redundant relationship
            db.delete(rel)
        else:
            rel.source_entity_id = src_id
            
    relationships_as_tgt = db.query(Relationship).filter(Relationship.target_entity_id == tgt_id).all()
    for rel in relationships_as_tgt:
        exists = db.query(Relationship).filter(
            Relationship.source_entity_id == rel.source_entity_id,
            Relationship.target_entity_id == src_id,
            Relationship.type == rel.type
        ).first()
        if exists:
            db.delete(rel)
        else:
            rel.target_entity_id = src_id
            
    # 2. Update all evidence links
    evidence_items = db.query(Evidence).filter(Evidence.entity_id == tgt_id).all()
    for ev in evidence_items:
        ev.entity_id = src_id
        
    # 3. Update all alerts
    alerts_items = db.query(Alert).filter(Alert.entity_id == tgt_id).all()
    for al in alerts_items:
        al.entity_id = src_id

    # 4. Remove Target Entity from Postgres and Neo4j
    db.delete(tgt)
    res.status = "MERGED"
    db.commit()

    # Re-sync Graph nodes to Neo4j
    GraphService.delete_entity_from_neo4j(tgt_id)
    # Sync source metadata update
    GraphService.sync_entity_to_neo4j(src_id, src.type, src.display_name, src.metadata_json)

    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="merge_entities",
        resource=f"source:{src_id}|target:{tgt_id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return {"success": True, "message": f"Successfully merged entity {tgt_id} into {src_id}"}
