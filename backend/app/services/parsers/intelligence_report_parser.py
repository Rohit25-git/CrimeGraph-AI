import csv
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.app.services.parsers.base_parser import (
    BaseSourceParser,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedEvidence,
    ParsedSourceResult
)
from backend.app.services.entity_extractor import EntityExtractor
from backend.app.services.relationship_extractor import RelationshipExtractor

logger = logging.getLogger("intelligence_report_parser")

class IntelligenceReportParser(BaseSourceParser):
    """Parser for Intelligence Agency Reports, Classified Briefings, and Informant Debriefs."""

    @property
    def source_type_name(self) -> str:
        return "INTELLIGENCE_REPORT"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["intel", "intelligence", "briefing", "agency_report", "informant", "threat_assessment"]):
            return True
        try:
            sample = content[:1500].decode("utf-8", errors="ignore").lower()
            keywords = ["intelligence report", "source assessment", "classified", "threat indicator", "agency briefing", "सूचना रिपोर्ट"]
            return any(kw in sample for kw in keywords)
        except Exception:
            return False

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        text = content.decode("utf-8", errors="ignore")
        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []
        raw_records: List[Dict[str, Any]] = []

        # 1. NLP Extraction for entities
        raw_entities = EntityExtractor.extract_entities(text)
        for re_ent in raw_entities:
            entities_map[re_ent["id"]] = ExtractedEntity(
                id=re_ent["id"],
                type=re_ent["type"],
                display_name=re_ent["display_name"],
                confidence=re_ent.get("confidence", 0.9),
                properties=re_ent.get("properties", {}),
                source_type="INTELLIGENCE_REPORT"
            )

        # 2. NLP Extraction for relationships
        raw_relationships = RelationshipExtractor.extract_relationships(text, raw_entities)
        for re_rel in raw_relationships:
            relationships.append(ExtractedRelationship(
                source_entity_id=re_rel["source_entity_id"],
                target_entity_id=re_rel["target_entity_id"],
                type=re_rel.get("type", "ASSOCIATED_WITH"),
                timestamp=datetime.utcnow(),
                confidence=re_rel.get("confidence", 0.85),
                properties=re_rel.get("properties", {}),
                source_type="INTELLIGENCE_REPORT",
                id=str(uuid.uuid4())
            ))

        # 3. Evidence provenance tracking
        evidence_list.append(ExtractedEvidence(
            type="INTELLIGENCE_REPORT",
            description=f"Intelligence Agency Briefing ({filename}): Corroborated {len(entities_map)} entities and {len(relationships)} structural links.",
            source_type="INTELLIGENCE_REPORT",
            properties={"briefing_source": filename, "entity_count": len(entities_map)}
        ))

        summary = f"Intelligence Agency report parsed from {filename}: {len(entities_map)} entities and {len(relationships)} relationships extracted via NLP pipeline."
        return ParsedSourceResult(
            source_type="INTELLIGENCE_REPORT",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=raw_records
        )
