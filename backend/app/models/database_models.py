import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import relationship
from backend.app.database.postgres import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="VIEWER", nullable=False)  # ADMIN, INVESTIGATOR, ANALYST, VIEWER
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    logs = relationship("AuditLog", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # CSV, JSON, PDF, TXT, etc.
    source_type = Column(String, default="GENERIC", nullable=False, index=True)  # CDR, FINANCIAL, FIR, SURVEILLANCE, SOCIAL_MEDIA, CRIMINAL_HISTORY, INTELLIGENCE_REPORT, GENERIC
    text_content = Column(Text, nullable=True)
    status = Column(String, default="PROCESSED", nullable=False)  # UPLOADED, PROCESSING, PROCESSED, ERROR
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")
    relationships = relationship("Relationship", back_populates="document", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="document", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(String, primary_key=True, index=True) # Unique ID (e.g. P001, PH001, V001)
    type = Column(String, nullable=False, index=True)  # PERSON, PHONE, VEHICLE, LOCATION, etc.
    display_name = Column(String, nullable=False, index=True)
    source_type = Column(String, default="GENERIC", nullable=False, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    confidence = Column(Float, default=1.0)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="entities")
    alerts = relationship("Alert", back_populates="entity", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="entity", cascade="all, delete-orphan")

class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(String, primary_key=True, index=True) # Unique relationship UUID
    source_entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False, index=True)  # CALLED, MESSAGED, MET, etc.
    source_type = Column(String, default="GENERIC", nullable=False, index=True)
    timestamp = Column(DateTime, nullable=True)
    confidence = Column(Float, default=1.0)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="relationships")
    evidence = relationship("Evidence", back_populates="relationship", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    
    document = relationship("Document", back_populates="events")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String, nullable=False, index=True)  # HIGH, MEDIUM, LOW, INFO
    title = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_json = Column(JSON, default=list, nullable=False)  # Transaction ids, CDR IDs, etc.
    status = Column(String, default="Requires Human Review", nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True)

    entity = relationship("Entity", back_populates="alerts")

class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # DOCUMENT, TRANSACTION, CDR, SURVEILLANCE
    source_type = Column(String, default="GENERIC", nullable=False, index=True)
    description = Column(Text, nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True)
    relationship_id = Column(String, ForeignKey("relationships.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="evidences")
    entity = relationship("Entity", back_populates="evidence")
    relationship = relationship("Relationship", back_populates="evidence")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False, index=True)  # login, upload, view, generate_report
    resource = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    result = Column(String, nullable=False)

    user = relationship("User", back_populates="logs")

class Investigation(Base):
    __tablename__ = "investigations"
    
    id = Column(String, primary_key=True, index=True) # e.g., INV-2026-001
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Active", nullable=False) # Active, Suspended, Closed
    priority = Column(String, default="Medium", nullable=False) # High, Medium, Low
    entities_json = Column(JSON, default=list, nullable=False) # List of associated entity IDs
    notes = Column(Text, nullable=True)

class EntityResolution(Base):
    __tablename__ = "entity_resolutions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, default=0.5)
    status = Column(String, default="PENDING", nullable=False) # PENDING, MERGED, REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

