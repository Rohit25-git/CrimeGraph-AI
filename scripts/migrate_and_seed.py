import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.postgres import engine, Base, get_db
from backend.app.models.database_models import User, Entity, Relationship, Document, Evidence, Alert
from backend.app.api.auth import get_password_hash
from backend.app.services.graph_service import GraphService

def migrate_and_seed():
    print("Migrating PostgreSQL tables...")
    with engine.connect() as conn:
        # Add source_type column to tables if not present
        conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE entities ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE evidence ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.commit()
    print("Schema migration completed successfully.")

    db = next(get_db())
    try:
        # Check entities count
        ent_count = db.query(Entity).count()
        print(f"Current entities in Postgres: {ent_count}")

        if ent_count == 0:
            print("Seeding initial investigative crime network dataset (Operation Nexus)...")
            
            doc = Document(
                filename="operation_nexus_master.txt",
                file_type="TXT",
                source_type="INTELLIGENCE_REPORT",
                text_content="Operation Nexus investigative intelligence dossier.",
                status="PROCESSED"
            )
            db.add(doc)
            db.commit()

            # Seed entities
            entities_data = [
                Entity(
                    id="P001",
                    type="PERSON",
                    display_name="Arjun Mehta",
                    source_type="CRIMINAL_HISTORY",
                    metadata_json={
                        "cctns_id": "CR-2024-912",
                        "criminal_history": [
                            {"offense": "Financial Hawala & Extortion", "disposition": "Under Trial", "sections": "IPC 420, 120B, 467", "case_number": "FIR-2024-88", "jurisdiction": "Mumbai Crime Branch", "date": "2024-03-15"},
                            {"offense": "Cyber Fraud Syndicate Operation", "disposition": "Bail Granted", "sections": "IT Act 66C, 66D", "case_number": "FIR-2023-14", "jurisdiction": "Delhi Cyber Police", "date": "2023-11-20"}
                        ]
                    },
                    confidence=0.98,
                    source_document_id=doc.id
                ),
                Entity(
                    id="P002",
                    type="PERSON",
                    display_name="Ravi Sharma",
                    source_type="SURVEILLANCE",
                    metadata_json={
                        "cctns_id": "CR-2025-104",
                        "criminal_history": [
                            {"offense": "Logistics & Transport Syndicate", "disposition": "Under Investigation", "sections": "IPC 120B", "case_number": "FIR-2025-02", "jurisdiction": "Gujarat State Police", "date": "2025-01-10"}
                        ]
                    },
                    confidence=0.94,
                    source_document_id=doc.id
                ),
                Entity(
                    id="P003",
                    type="PERSON",
                    display_name="Sameer Khan",
                    source_type="FIR",
                    metadata_json={"role": "Account Facilitator"},
                    confidence=0.92,
                    source_document_id=doc.id
                ),
                Entity(
                    id="P004",
                    type="PERSON",
                    display_name="Vikram Das",
                    source_type="FINANCIAL",
                    metadata_json={"role": "Hawala Courier"},
                    confidence=0.88,
                    source_document_id=doc.id
                ),
                Entity(
                    id="PH001",
                    type="PHONE",
                    display_name="+919876543210",
                    source_type="CDR",
                    metadata_json={"service_provider": "Airtel", "imei": "864209041234567"},
                    confidence=0.99,
                    source_document_id=doc.id
                ),
                Entity(
                    id="PH002",
                    type="PHONE",
                    display_name="+919812345678",
                    source_type="CDR",
                    metadata_json={"service_provider": "Jio", "imei": "864209049876543"},
                    confidence=0.99,
                    source_document_id=doc.id
                ),
                Entity(
                    id="LOC001",
                    type="LOCATION",
                    display_name="Nariman Point, Mumbai",
                    source_type="FIR",
                    metadata_json={"coordinates": "18.9256, 72.8242"},
                    confidence=0.95,
                    source_document_id=doc.id
                ),
                Entity(
                    id="LOC002",
                    type="LOCATION",
                    display_name="Bandra Kurla Complex",
                    source_type="SURVEILLANCE",
                    metadata_json={"coordinates": "19.0657, 72.8687"},
                    confidence=0.95,
                    source_document_id=doc.id
                ),
                Entity(
                    id="VEH001",
                    type="VEHICLE",
                    display_name="MH01AB1234 (Black Fortuner)",
                    source_type="SURVEILLANCE",
                    metadata_json={"owner": "Ravi Sharma"},
                    confidence=0.96,
                    source_document_id=doc.id
                ),
                Entity(
                    id="ACC001",
                    type="BANK_ACCOUNT",
                    display_name="SBI-A/C-98765432",
                    source_type="FINANCIAL",
                    metadata_json={"branch": "Mumbai Fort", "ifsc": "SBIN0000300"},
                    confidence=0.99,
                    source_document_id=doc.id
                ),
                Entity(
                    id="ACC002",
                    type="BANK_ACCOUNT",
                    display_name="HDFC-A/C-11223344",
                    source_type="FINANCIAL",
                    metadata_json={"branch": "BKC", "ifsc": "HDFC0000123"},
                    confidence=0.99,
                    source_document_id=doc.id
                ),
                Entity(
                    id="ORG001",
                    type="ORGANIZATION",
                    display_name="Apex Logistics & Trade Pvt Ltd",
                    source_type="FIR",
                    metadata_json={"cin": "U74999MH2021PTC123456"},
                    confidence=0.91,
                    source_document_id=doc.id
                )
            ]

            for e in entities_data:
                db.add(e)
            db.commit()

            # Seed relationships
            relationships_data = [
                Relationship(id="R001", source_entity_id="P001", target_entity_id="PH001", type="USES", source_type="CDR", confidence=0.99, source_document_id=doc.id),
                Relationship(id="R002", source_entity_id="P002", target_entity_id="PH002", type="USES", source_type="CDR", confidence=0.99, source_document_id=doc.id),
                Relationship(id="R003", source_entity_id="PH001", target_entity_id="PH002", type="CALLED", source_type="CDR", confidence=0.95, source_document_id=doc.id, metadata_json={"call_count": 42, "total_duration_sec": 3600}),
                Relationship(id="R004", source_entity_id="P001", target_entity_id="P002", type="MET_WITH", source_type="SURVEILLANCE", confidence=0.93, source_document_id=doc.id),
                Relationship(id="R005", source_entity_id="P002", target_entity_id="VEH001", type="DRIVING", source_type="SURVEILLANCE", confidence=0.97, source_document_id=doc.id),
                Relationship(id="R006", source_entity_id="P001", target_entity_id="LOC001", type="VISITED", source_type="FIR", confidence=0.92, source_document_id=doc.id),
                Relationship(id="R007", source_entity_id="P002", target_entity_id="LOC002", type="SPOTTED_AT", source_type="SURVEILLANCE", confidence=0.94, source_document_id=doc.id),
                Relationship(id="R008", source_entity_id="P001", target_entity_id="ACC001", type="CONTROLS", source_type="FINANCIAL", confidence=0.98, source_document_id=doc.id),
                Relationship(id="R009", source_entity_id="ACC001", target_entity_id="ACC002", type="TRANSFERRED_TO", source_type="FINANCIAL", confidence=0.99, source_document_id=doc.id, metadata_json={"amount": 1500000, "currency": "INR"}),
                Relationship(id="R010", source_entity_id="ACC002", target_entity_id="P004", type="TRANSFERRED_TO", source_type="FINANCIAL", confidence=0.96, source_document_id=doc.id, metadata_json={"amount": 1450000, "currency": "INR"}),
                Relationship(id="R011", source_entity_id="P004", target_entity_id="P001", type="TRANSFERRED_TO", source_type="FINANCIAL", confidence=0.95, source_document_id=doc.id, metadata_json={"amount": 1400000, "currency": "INR", "note": "Circular transfer return"}),
                Relationship(id="R012", source_entity_id="P001", target_entity_id="P003", type="COMMUNICATED_WITH", source_type="SOCIAL_MEDIA", confidence=0.91, source_document_id=doc.id),
                Relationship(id="R013", source_entity_id="P003", target_entity_id="ORG001", type="DIRECTOR_OF", source_type="FIR", confidence=0.96, source_document_id=doc.id),
                Relationship(id="R014", source_entity_id="P001", target_entity_id="ORG001", type="BENEFICIAL_OWNER", source_type="FIR", confidence=0.89, source_document_id=doc.id)
            ]

            for r in relationships_data:
                db.add(r)
            db.commit()

            # Seed evidence
            evidences = [
                Evidence(type="CDR", source_type="CDR", description="42 voice calls logged between +919876543210 (Arjun Mehta) and +919812345678 (Ravi Sharma)", entity_id="P001", relationship_id="R003", source_document_id=doc.id, source_document_name=doc.filename),
                Evidence(type="FINANCIAL", source_type="FINANCIAL", description="Circular Hawala transfer: SBI-A/C-98765432 -> HDFC-A/C-11223344 -> Vikram Das -> Arjun Mehta (Rs 15,00,000)", entity_id="P001", relationship_id="R009", source_document_id=doc.id, source_document_name=doc.filename),
                Evidence(type="SURVEILLANCE", source_type="SURVEILLANCE", description="Physical stakeout observed Arjun Mehta and Ravi Sharma at Bandra Kurla Complex with Black Fortuner MH01AB1234", entity_id="P002", relationship_id="R004", source_document_id=doc.id, source_document_name=doc.filename)
            ]
            for ev in evidences:
                db.add(ev)
            db.commit()

            # Seed alert
            alert = Alert(
                severity="HIGH",
                title="Circular Hawala Money Flow Detected",
                reason="Funds cycled from Arjun Mehta (SBI A/C) through HDFC account to Vikram Das and back to Arjun Mehta within 48 hours.",
                evidence_json=[{"type": "FINANCIAL", "relationship_id": "R009"}, {"type": "FINANCIAL", "relationship_id": "R011"}],
                status="UNRESOLVED",
                entity_id="P001"
            )
            db.add(alert)
            db.commit()

            print("Database seeded with Operation Nexus entities, relationships, evidence, and alerts!")

            # Sync to Neo4j if available
            for e in entities_data:
                GraphService.sync_entity_to_neo4j(e.id, e.type, e.display_name, e.metadata_json)
            for r in relationships_data:
                GraphService.sync_relationship_to_neo4j(r.id, r.source_entity_id, r.target_entity_id, r.type, r.timestamp, r.metadata_json)

            print("All entities synced to Graph layer!")
        else:
            print(f"Database already populated ({ent_count} entities).")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_and_seed()
