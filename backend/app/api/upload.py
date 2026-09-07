from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.app.database.postgres import get_db
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.models.database_models import User, Document, Entity, Relationship, Evidence, AuditLog
from backend.app.schemas.schemas import DocumentResponse
from backend.app.services.parsers.registry import ParserRegistry
from backend.app.services.graph_service import GraphService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/api/upload", tags=["Data Ingestion"])

# Allow INVESTIGATOR and ANALYST to upload
allow_upload = RoleChecker(["ADMIN", "ANALYST", "INVESTIGATOR"])

@router.get("/sources", response_model=List[str])
async def get_supported_sources():
    """Returns the list of supported source ingestion connector types."""
    return ParserRegistry.list_supported_sources()

@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    source_type: Optional[str] = Query(None, description="Explicit source connector (CDR, FINANCIAL, FIR, SURVEILLANCE, SOCIAL_MEDIA, CRIMINAL_HISTORY, INTELLIGENCE_REPORT, AUTO)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_upload)
):
    # 1. Validate file extension
    filename = file.filename or ""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    allowed_extensions = {"txt", "csv", "json", "pdf", "docx"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: .{ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    # 2. Read content & validate size (Max 25MB)
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read file content: {e}"
        )
        
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds size limit of 10MB (Got {len(content)/(1024*1024):.1f}MB)"
        )

    # 3. Resolve Parser & Parse Source Content
    parser = ParserRegistry.get_parser(source_type=source_type, content=content, filename=filename)
    resolved_source_type = parser.source_type_name

    # 4. Insert Document record (initially PROCESSING)
    db_doc = Document(
        filename=filename,
        file_type=ext.upper(),
        source_type=resolved_source_type,
        text_content="",
        status="PROCESSING",
        confidence=1.0
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    try:
        # Execute format-aware parsing
        parse_result = parser.parse(content, filename)
        db_doc.text_content = parse_result.text_summary
        db_doc.source_type = parse_result.source_type
        db.commit()

        # 5. Save and sync entities
        for ent_data in parse_result.entities:
            ent_id = ent_data.id
            db_ent = db.query(Entity).filter(Entity.id == ent_id).first()
            if not db_ent:
                db_ent = Entity(
                    id=ent_id,
                    type=ent_data.type,
                    display_name=ent_data.display_name,
                    source_type=ent_data.source_type,
                    metadata_json=ent_data.properties,
                    confidence=ent_data.confidence,
                    source_document_id=db_doc.id
                )
                db.add(db_ent)
            else:
                # Merge properties and criminal history if present
                db_ent.source_document_id = db_doc.id
                updated_meta = dict(db_ent.metadata_json or {})
                for k, v in ent_data.properties.items():
                    if k == "criminal_history" and isinstance(v, list):
                        existing_hist = updated_meta.setdefault("criminal_history", [])
                        existing_hist.extend(v)
                    else:
                        updated_meta[k] = v
                db_ent.metadata_json = updated_meta
            
            db.commit()
            
            # Sync to Neo4j
            GraphService.sync_entity_to_neo4j(
                ent_id, db_ent.type, db_ent.display_name, db_ent.metadata_json
            )
            
            # Save Document Evidence
            EvidenceService.add_evidence(
                db, 
                evidence_type="DOCUMENT", 
                description=f"Ingested {db_ent.type} entity {db_ent.display_name} ({ent_id}) from source {db_doc.source_type} [{db_doc.filename}].", 
                source_document_id=db_doc.id, 
                entity_id=ent_id
            )

        # 6. Save and sync relationships
        for rel_data in parse_result.relationships:
            rel_id = rel_data.id or str(uuid.uuid4())
            db_rel = Relationship(
                id=rel_id,
                source_entity_id=rel_data.source_entity_id,
                target_entity_id=rel_data.target_entity_id,
                type=rel_data.type,
                source_type=rel_data.source_type,
                timestamp=rel_data.timestamp or datetime.utcnow(),
                confidence=rel_data.confidence,
                source_document_id=db_doc.id,
                metadata_json=rel_data.properties
            )
            db.add(db_rel)
            db.commit()
            
            # Sync to Neo4j
            GraphService.sync_relationship_to_neo4j(
                rel_id, db_rel.source_entity_id, db_rel.target_entity_id, db_rel.type, db_rel.timestamp, db_rel.metadata_json
            )
            
            # Save Evidence
            EvidenceService.add_evidence(
                db,
                evidence_type=db_doc.source_type,
                description=f"Extracted {db_rel.type} relationship ({db_rel.source_entity_id} ➔ {db_rel.target_entity_id}) from {db_doc.source_type} record.",
                source_document_id=db_doc.id,
                relationship_id=rel_id
            )

        # 7. Save custom Evidence provenance citations from parser
        for ev_data in parse_result.evidence:
            db_ev = Evidence(
                type=ev_data.type,
                source_type=ev_data.source_type,
                description=ev_data.description,
                source_document_id=db_doc.id,
                entity_id=ev_data.entity_id,
                relationship_id=ev_data.relationship_id
            )
            db.add(db_ev)
        db.commit()

        # Ingestion Complete
        db_doc.status = "PROCESSED"
        db.commit()

        # 8. Run Anomaly Detection to update alerts in real-time
        AnomalyService.detect_all_anomalies(db)

        # Audit logging
        log = AuditLog(
            user_id=current_user.id,
            action="upload_document",
            resource=f"document:{db_doc.filename}:{db_doc.source_type}",
            result="SUCCESS",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()

        return db_doc

    except Exception as e:
        db_doc.status = "ERROR"
        db.commit()
        
        # Log failure
        log = AuditLog(
            user_id=current_user.id,
            action="upload_document",
            resource=f"document:{file.filename}:{resolved_source_type}",
            result=f"ERROR: {str(e)}",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing uploaded document with {resolved_source_type} parser: {e}"
        )
