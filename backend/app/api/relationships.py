from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from typing import List, Optional

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Relationship, Entity, AuditLog
from backend.app.schemas.schemas import RelationshipResponse, RelationshipCreate
from backend.app.services.graph_service import GraphService
from backend.app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/api/relationships", tags=["Relationships"])

read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.get("", response_model=List[RelationshipResponse])
def get_relationships(
    source: Optional[str] = Query(None, description="Filter by source entity ID"),
    target: Optional[str] = Query(None, description="Filter by target entity ID"),
    type: Optional[str] = Query(None, description="Filter by relationship type (e.g. CALLED)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    query = db.query(Relationship)
    if source:
        query = query.filter(Relationship.source_entity_id == source)
    if target:
        query = query.filter(Relationship.target_entity_id == target)
    if type:
        query = query.filter(Relationship.type == type.upper())
        
    return query.offset(offset).limit(limit).all()

@router.get("/{id}", response_model=RelationshipResponse)
def get_relationship(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    rel = db.query(Relationship).filter(Relationship.id == id).first()
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship with ID {id} not found"
        )
    return rel

@router.get("/{id}/evidence")
def get_relationship_evidence(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    rel = db.query(Relationship).filter(Relationship.id == id).first()
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship with ID {id} not found"
        )
    return EvidenceService.get_evidence_for_relationship(db, id)

@router.post("", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(
    rel_in: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    # Verify source and target exist
    src = db.query(Entity).filter(Entity.id == rel_in.source_entity_id).first()
    tgt = db.query(Entity).filter(Entity.id == rel_in.target_entity_id).first()
    if not src or not tgt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source or Target entity does not exist"
        )
        
    rel_id = rel_in.id or str(uuid.uuid4())
    
    # Check if ID already exists
    existing = db.query(Relationship).filter(Relationship.id == rel_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Relationship with ID {rel_id} already exists"
        )
        
    db_rel = Relationship(
        id=rel_id,
        source_entity_id=rel_in.source_entity_id,
        target_entity_id=rel_in.target_entity_id,
        type=rel_in.type.upper(),
        timestamp=rel_in.timestamp,
        confidence=rel_in.confidence,
        source_document_id=rel_in.source_document_id,
        metadata_json=rel_in.metadata_json or {}
    )
    
    db.add(db_rel)
    db.commit()
    db.refresh(db_rel)
    
    # Sync to Neo4j
    GraphService.sync_relationship_to_neo4j(
        db_rel.id, db_rel.source_entity_id, db_rel.target_entity_id, db_rel.type, db_rel.timestamp, db_rel.metadata_json
    )
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="create_relationship",
        resource=f"relationship:{db_rel.id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return db_rel

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_relationship(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    db_rel = db.query(Relationship).filter(Relationship.id == id).first()
    if not db_rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship with ID {id} not found"
        )
        
    db.delete(db_rel)
    db.commit()
    
    # Delete from Neo4j
    GraphService.delete_relationship_from_neo4j(id)
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="delete_relationship",
        resource=f"relationship:{id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"success": True, "message": f"Relationship {id} successfully deleted"}
