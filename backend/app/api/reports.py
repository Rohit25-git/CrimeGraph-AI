from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Entity, Relationship, Alert, Document, Evidence, AuditLog
from backend.app.schemas.schemas import ReportRequest, ReportResponse
from backend.app.services.graph_service import GraphService
from backend.app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/api/reports", tags=["Investigation Reports"])

write_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

@router.post("", response_model=ReportResponse)
def generate_report(
    req: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(write_roles)
):
    selected_ids = req.selected_entity_ids
    if not selected_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one entity ID must be specified to generate a report."
        )

    # 1. Fetch selected entities
    entities_db = db.query(Entity).filter(Entity.id.in_(selected_ids)).all()
    if not entities_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="None of the specified entity IDs were found in the database."
        )

    # 2. Gather metrics
    centralities = GraphService.compute_centrality(db)
    communities = GraphService.detect_communities(db)

    entities_data = []
    for ent in entities_db:
        entities_data.append({
            "id": ent.id,
            "type": ent.type,
            "display_name": ent.display_name,
            "influence_score": centralities.get("pagerank", {}).get(ent.id, 0.0),
            "betweenness_score": centralities.get("betweenness", {}).get(ent.id, 0.0),
            "community_id": communities.get(ent.id, -1),
            "metadata": ent.metadata_json
        })

    # 3. Fetch relationships between selected entities
    rels_db = db.query(Relationship).filter(
        (Relationship.source_entity_id.in_(selected_ids)) & 
        (Relationship.target_entity_id.in_(selected_ids))
    ).all()
    
    relationships_data = []
    for rel in rels_db:
        relationships_data.append({
            "id": rel.id,
            "source": rel.source_entity_id,
            "target": rel.target_entity_id,
            "type": rel.type,
            "timestamp": rel.timestamp.isoformat() if rel.timestamp else None,
            "confidence": rel.confidence,
            "metadata": rel.metadata_json
        })

    # 4. Fetch timeline events & relationships with timestamps (Chronological timeline)
    timeline_items = []
    for rel in rels_db:
        if rel.timestamp:
            timeline_items.append({
                "timestamp": rel.timestamp.isoformat(),
                "description": f"{rel.source_entity_id} ({rel.type}) {rel.target_entity_id}",
                "evidence_ref": f"rel:{rel.id}"
            })
            
    # Add alerts to timeline if they involve selected entities
    alerts_db = db.query(Alert).filter(Alert.entity_id.in_(selected_ids)).all()
    anomalies_data = []
    for alert in alerts_db:
        anomalies_data.append({
            "id": alert.id,
            "severity": alert.severity,
            "title": alert.title,
            "reason": alert.reason,
            "status": alert.status,
            "timestamp": alert.timestamp.isoformat(),
            "entity_id": alert.entity_id
        })
        timeline_items.append({
            "timestamp": alert.timestamp.isoformat(),
            "description": f"ALERT ({alert.severity}): {alert.title} on {alert.entity_id}",
            "evidence_ref": f"alert:{alert.id}"
        })
        
    # Sort timeline by timestamp ascending
    timeline_items.sort(key=lambda x: x["timestamp"])

    # 5. Fetch evidence & source documents
    evidence_data = []
    sources_data = []
    seen_docs = set()
    
    for ent_id in selected_ids:
        evs = EvidenceService.get_evidence_for_entity(db, ent_id)
        for ev in evs:
            evidence_data.append(ev)
            if ev["source_document_id"] and ev["source_document_id"] not in seen_docs:
                seen_docs.add(ev["source_document_id"])
                
    for rel in rels_db:
        evs = EvidenceService.get_evidence_for_relationship(db, rel.id)
        for ev in evs:
            evidence_data.append(ev)
            if ev["source_document_id"] and ev["source_document_id"] not in seen_docs:
                seen_docs.add(ev["source_document_id"])

    if seen_docs:
        docs = db.query(Document).filter(Document.id.in_(list(seen_docs))).all()
        for doc in docs:
            sources_data.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "created_at": doc.created_at.isoformat()
            })

    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"

    # Log to audit logs
    log = AuditLog(
        user_id=current_user.id,
        action="generate_report",
        resource=f"report:{report_id}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    return {
        "report_id": report_id,
        "investigation_name": req.investigation_name,
        "generated_at": datetime.utcnow(),
        "network_summary": {
            "total_selected_entities": len(entities_data),
            "total_relationships": len(relationships_data),
            "total_alerts": len(anomalies_data)
        },
        "metrics": {
            "communities_count": len(set(communities.get(eid) for eid in selected_ids if communities.get(eid) is not None))
        },
        "entities": entities_data,
        "relationships": relationships_data,
        "timeline": timeline_items,
        "anomalies": anomalies_data,
        "evidence": evidence_data,
        "sources": sources_data
    }
