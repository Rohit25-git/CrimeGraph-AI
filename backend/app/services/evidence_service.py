from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.models.database_models import Evidence, Document, Relationship, Entity

class EvidenceService:
    @staticmethod
    def add_evidence(
        db: Session, 
        evidence_type: str, 
        description: str, 
        source_document_id: int = None, 
        entity_id: str = None, 
        relationship_id: str = None
    ) -> Evidence:
        """Adds a piece of evidence to the database linking to a source document."""
        ev = Evidence(
            type=evidence_type,
            description=description,
            source_document_id=source_document_id,
            entity_id=entity_id,
            relationship_id=relationship_id
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def get_evidence_for_entity(db: Session, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieves all evidence and documents related to an entity."""
        evidences = db.query(Evidence).filter(Evidence.entity_id == entity_id).all()
        results = []
        for ev in evidences:
            doc = db.query(Document).filter(Document.id == ev.source_document_id).first() if ev.source_document_id else None
            results.append({
                "id": ev.id,
                "type": ev.type,
                "description": ev.description,
                "source_document_id": ev.source_document_id,
                "source_document_name": doc.filename if doc else "Manual Entry",
                "created_at": ev.created_at.isoformat()
            })
        return results

    @staticmethod
    def get_evidence_for_relationship(db: Session, relationship_id: str) -> List[Dict[str, Any]]:
        """Retrieves all evidence and documents related to a relationship."""
        evidences = db.query(Evidence).filter(Evidence.relationship_id == relationship_id).all()
        results = []
        for ev in evidences:
            doc = db.query(Document).filter(Document.id == ev.source_document_id).first() if ev.source_document_id else None
            results.append({
                "id": ev.id,
                "type": ev.type,
                "description": ev.description,
                "source_document_id": ev.source_document_id,
                "source_document_name": doc.filename if doc else "Manual Entry",
                "created_at": ev.created_at.isoformat()
            })
        return results
