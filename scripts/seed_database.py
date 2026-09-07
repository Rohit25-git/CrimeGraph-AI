import os
import sys
import json
import csv
import uuid
from datetime import datetime

# Adjust path to import backend
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.app.database.postgres import SessionLocal, engine, Base
from backend.app.models.database_models import Entity, Relationship, Document, User, Alert, Evidence, AuditLog, Investigation, EntityResolution
from backend.app.services.graph_service import GraphService
from backend.app.services.anomaly_service import AnomalyService
from backend.app.services.evidence_service import EvidenceService

DATA_DIR = "C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data"

def seed_db():
    print("Auto-generating large synthetic crime network dataset (500+ relationships)...")
    # Import and run data generator
    from scripts.generate_demo_data import generate_data
    generate_data()

    print("Re-creating database schemas...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Create Default User
        from backend.app.api.auth import get_password_hash
        hashed_pwd = get_password_hash("password")
        investigator = User(
            username="investigator",
            hashed_password=hashed_pwd,
            role="ADMIN"
        )
        db.add(investigator)
        db.commit()
        print("Created default user: investigator / password")

        # 2. Ingest the Intelligence Report as a Document
        report_path = f"{DATA_DIR}/intelligence/intel_report_01.txt"
        with open(report_path, "r") as f:
            report_text = f.read()

        db_doc = Document(
            filename="intel_report_01.txt",
            file_type="TXT",
            text_content=report_text,
            status="PROCESSED",
            confidence=1.0
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        print("Ingested intelligence report document.")

        # 3. Seed Entities (Persons, Phones, Vehicles, Locations, Organizations)
        entity_files = [
            ("persons.json", "PERSON"),
            ("phones.json", "PHONE"),
            ("vehicles.json", "VEHICLE"),
            ("locations.json", "LOCATION"),
            ("organizations.json", "ORGANIZATION")
        ]

        entity_count = 0
        for filename, ent_type in entity_files:
            filepath = f"{DATA_DIR}/{filename}"
            with open(filepath, "r") as f:
                items = json.load(f)
                
            for item in items:
                db_ent = Entity(
                    id=item["id"],
                    type=ent_type,
                    display_name=item["name"] if "name" in item else item.get("plate") or item.get("number") or item["id"],
                    metadata_json=item.get("properties", {}),
                    confidence=1.0,
                    source_document_id=db_doc.id if item["id"] in ["P001", "P002", "P003", "LOC001", "LOC002", "V001"] else None
                )
                db.add(db_ent)
                entity_count += 1
                
                # Sync node to Neo4j
                GraphService.sync_entity_to_neo4j(
                    db_ent.id, db_ent.type, db_ent.display_name, db_ent.metadata_json
                )
                
                # If connected to source doc, add evidence
                if db_ent.source_document_id:
                    EvidenceService.add_evidence(
                        db,
                        evidence_type="DOCUMENT",
                        description=f"Extracted entity {db_ent.display_name} from report narrative.",
                        source_document_id=db_doc.id,
                        entity_id=db_ent.id
                    )

        db.commit()
        print(f"Seeded {entity_count} entities in PostgreSQL & Neo4j.")

        # 4. Seed Relationships
        relationships_path = f"{DATA_DIR}/relationships.csv"
        rel_count = 0
        with open(relationships_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rel_id = str(uuid.uuid4())
                ts = datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None
                amount = float(row["amount"]) if row["amount"] else 0.0
                
                # Store properties
                properties = {}
                if amount > 0:
                    properties["amount"] = amount
                if row["source_id"] in ["P001", "P002", "P003"] and row["target_id"] in ["P001", "P002", "P003", "LOC001", "LOC002", "V001"]:
                    source_doc_id = db_doc.id
                else:
                    source_doc_id = None
                    
                db_rel = Relationship(
                    id=rel_id,
                    source_entity_id=row["source_id"],
                    target_entity_id=row["target_id"],
                    type=row["rel_type"],
                    timestamp=ts,
                    confidence=1.0,
                    source_document_id=source_doc_id,
                    metadata_json=properties
                )
                db.add(db_rel)
                rel_count += 1

                # Sync edge to Neo4j
                GraphService.sync_relationship_to_neo4j(
                    rel_id, db_rel.source_entity_id, db_rel.target_entity_id, db_rel.type, db_rel.timestamp, db_rel.metadata_json
                )

                # Add evidence if from report
                if db_rel.source_document_id:
                    EvidenceService.add_evidence(
                        db,
                        evidence_type="DOCUMENT",
                        description=f"Extracted relationship {db_rel.type} from report narrative.",
                        source_document_id=db_doc.id,
                        relationship_id=rel_id
                    )

        db.commit()
        print(f"Seeded {rel_count} relationships in PostgreSQL & Neo4j.")

        # 5. Seed extra Person nodes for Entity Resolution demo
        ent151 = Entity(
            id="P151",
            type="PERSON",
            display_name="R. Sharma",
            metadata_json={"occupation": "Logistics Consultant", "age": 39},
            confidence=0.88
        )
        ent152 = Entity(
            id="P152",
            type="PERSON",
            display_name="Sameer K.",
            metadata_json={"occupation": "Finance Specialist", "age": 44},
            confidence=0.82
        )
        db.add(ent151)
        db.add(ent152)
        db.commit()

        # Sync to Neo4j
        GraphService.sync_entity_to_neo4j("P151", "PERSON", "R. Sharma", {"occupation": "Logistics Consultant", "age": 39})
        GraphService.sync_entity_to_neo4j("P152", "PERSON", "Sameer K.", {"occupation": "Finance Specialist", "age": 44})

        # Seed Entity Resolution suggestions
        res1 = EntityResolution(
            source_entity_id="P002",
            target_entity_id="P151",
            confidence=0.83,
            status="PENDING"
        )
        res2 = EntityResolution(
            source_entity_id="P003",
            target_entity_id="P152",
            confidence=0.78,
            status="PENDING"
        )
        db.add(res1)
        db.add(res2)


        # 6. Seed Investigations (Cases)
        inv1 = Investigation(
            id="INV-2026-001",
            title="Operation Nexus",
            description="Network analysis of import/export logistics and financial anomalies revolving around Arjun Mehta.",
            created_by="investigator",
            status="Active",
            priority="High",
            entities_json=["P001", "P002", "P003", "P004", "LOC001", "V001"],
            notes="Focusing on shipping schedules and transaction loops connecting Bandra Safehouse and Nhava Sheva Custom points."
        )
        inv2 = Investigation(
            id="INV-2026-002",
            title="Operation Monsoon",
            description="Preliminary tracking of maritime logistic clusters and potential cross-community bridge connections.",
            created_by="investigator",
            status="Archived",
            priority="Medium",
            entities_json=["P005", "P006", "P007"],
            notes="Initial review completed. Case is archived but files remain searchable."
        )
        db.add(inv1)
        db.add(inv2)
        db.commit()
        print("Seeded Investigations and Entity Resolution suggests in PostgreSQL.")

        # 7. Run Anomaly Detection Models
        print("Running investigative anomaly detection models...")
        alert_count = AnomalyService.detect_all_anomalies(db)
        print(f"Generated {alert_count} active investigative alerts/anomalies.")

        # 8. Seed a sample audit log entry
        log = AuditLog(
            user_id=investigator.id,
            action="seed_database",
            resource="system",
            result="SUCCESS",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()

        print("Database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
