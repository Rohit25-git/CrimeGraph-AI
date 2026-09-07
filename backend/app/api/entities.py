from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Entity, AuditLog
from backend.app.schemas.schemas import EntityResponse, EntityCreate
from backend.app.services.graph_service import GraphService
from backend.app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/api/entities", tags=["Entities"])

# Roles configuration
read_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST", "VIEWER"])
write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.get("", response_model=List[EntityResponse])
def get_entities(
    q: Optional[str] = Query(None, description="Search query for display name or ID"),
    type: Optional[str] = Query(None, description="Filter by entity type (e.g. PERSON)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    query = db.query(Entity)
    if type:
        query = query.filter(Entity.type == type.upper())
    if q:
        query = query.filter(
            (Entity.display_name.ilike(f"%{q}%")) | 
            (Entity.id.ilike(f"%{q}%"))
        )
    return query.offset(offset).limit(limit).all()

@router.get("/{id}", response_model=EntityResponse)
def get_entity(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    entity = db.query(Entity).filter(Entity.id == id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID {id} not found"
        )
    return entity

@router.get("/{id}/connections")
def get_entity_connections(
    id: str,
    depth: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    # Verify entity exists
    entity = db.query(Entity).filter(Entity.id == id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID {id} not found"
        )
        
    neighborhood = GraphService.get_neighborhood(db, id, depth)
    return neighborhood

@router.get("/{id}/evidence")
def get_entity_evidence(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_roles)
):
    entity = db.query(Entity).filter(Entity.id == id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID {id} not found"
        )
    return EvidenceService.get_evidence_for_entity(db, id)

@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(
    entity_in: EntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    # Check if ID already exists
    existing = db.query(Entity).filter(Entity.id == entity_in.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entity with ID {entity_in.id} already exists"
        )
        
    db_ent = Entity(
        id=entity_in.id,
        type=entity_in.type.upper(),
        display_name=entity_in.display_name,
        metadata_json=entity_in.metadata_json or {},
        confidence=entity_in.confidence,
        source_document_id=entity_in.source_document_id
    )
    db.add(db_ent)
    db.commit()
    db.refresh(db_ent)
    
    # Sync to Neo4j
    GraphService.sync_entity_to_neo4j(
        db_ent.id, db_ent.type, db_ent.display_name, db_ent.metadata_json
    )
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="create_entity",
        resource=f"entity:{db_ent.id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return db_ent

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_entity(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    db_ent = db.query(Entity).filter(Entity.id == id).first()
    if not db_ent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID {id} not found"
        )
        
    db.delete(db_ent)
    db.commit()
    
    # Delete from Neo4j
    GraphService.delete_entity_from_neo4j(id)
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id,
        action="delete_entity",
        resource=f"entity:{id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"success": True, "message": f"Entity {id} successfully deleted"}
