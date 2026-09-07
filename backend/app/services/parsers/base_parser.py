from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class ExtractedEntity:
    id: str
    type: str  # PERSON, PHONE, VEHICLE, LOCATION, ORGANIZATION, BANK_ACCOUNT
    display_name: str
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    source_type: str = "GENERIC"

@dataclass
class ExtractedRelationship:
    source_entity_id: str
    target_entity_id: str
    type: str  # CALLED, MESSAGED, MET, TRANSFERRED_TO, OWNS, USES, INVOLVED_IN, ACCUSED_OF, CONNECTED_ON_SOCIAL, etc.
    timestamp: Optional[datetime] = None
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    source_type: str = "GENERIC"
    id: Optional[str] = None

@dataclass
class ExtractedEvidence:
    type: str  # CDR, TRANSACTION, FIR, SURVEILLANCE, SOCIAL_MEDIA, CRIMINAL_HISTORY, INTELLIGENCE_REPORT, DOCUMENT
    description: str
    source_type: str = "GENERIC"
    entity_id: Optional[str] = None
    relationship_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParsedSourceResult:
    source_type: str
    text_summary: str
    entities: List[ExtractedEntity] = field(default_factory=list)
    relationships: List[ExtractedRelationship] = field(default_factory=list)
    evidence: List[ExtractedEvidence] = field(default_factory=list)
    raw_records: List[Dict[str, Any]] = field(default_factory=list)

class BaseSourceParser(ABC):
    """Abstract Base Class for all format-aware source ingestion connectors."""
    
    @property
    @abstractmethod
    def source_type_name(self) -> str:
        """Returns the canonical source_type identifier (e.g. CDR, FINANCIAL, FIR, etc.)."""
        pass

    @abstractmethod
    def can_parse(self, content: bytes, filename: str) -> bool:
        """Heuristic check to determine if this parser can handle the provided file."""
        pass

    @abstractmethod
    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        """Parses file bytes into standardized entities, relationships, and evidence provenance records."""
        pass
