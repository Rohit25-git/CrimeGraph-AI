import logging
from typing import Dict, List, Optional, Type
import uuid
from datetime import datetime

from backend.app.services.parsers.base_parser import (
    BaseSourceParser,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractedEvidence,
    ParsedSourceResult
)
from backend.app.services.parsers.cdr_parser import CDRParser
from backend.app.services.parsers.financial_parser import FinancialTransactionParser
from backend.app.services.parsers.fir_parser import FIRParser
from backend.app.services.parsers.surveillance_parser import SurveillanceReportParser
from backend.app.services.parsers.social_media_parser import SocialMediaParser
from backend.app.services.parsers.criminal_history_parser import CriminalHistoryParser
from backend.app.services.parsers.intelligence_report_parser import IntelligenceReportParser
from backend.app.services.entity_extractor import EntityExtractor
from backend.app.services.relationship_extractor import RelationshipExtractor
from backend.app.services.document_processor import DocumentProcessor

logger = logging.getLogger("parser_registry")

class GenericDocumentParser(BaseSourceParser):
    """Fallback parser for generic narrative text, unstructured notes, or standard documents."""

    @property
    def source_type_name(self) -> str:
        return "GENERIC"

    def can_parse(self, content: bytes, filename: str) -> bool:
        return True

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, any]] = None) -> ParsedSourceResult:
        parsed_doc = DocumentProcessor.process_file(content, filename)
        text = parsed_doc.get("text", "")
        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []

        if parsed_doc.get("type") in ["unstructured", "binary_document"]:
            raw_entities = EntityExtractor.extract_entities(text)
            for re_ent in raw_entities:
                entities_map[re_ent["id"]] = ExtractedEntity(
                    id=re_ent["id"],
                    type=re_ent["type"],
                    display_name=re_ent["display_name"],
                    confidence=re_ent.get("confidence", 0.9),
                    properties=re_ent.get("properties", {}),
                    source_type="GENERIC"
                )

            raw_relationships = RelationshipExtractor.extract_relationships(text, raw_entities)
            for re_rel in raw_relationships:
                relationships.append(ExtractedRelationship(
                    source_entity_id=re_rel["source_entity_id"],
                    target_entity_id=re_rel["target_entity_id"],
                    type=re_rel.get("type", "ASSOCIATED_WITH"),
                    timestamp=datetime.utcnow(),
                    confidence=re_rel.get("confidence", 0.8),
                    properties=re_rel.get("properties", {}),
                    source_type="GENERIC",
                    id=str(uuid.uuid4())
                ))
        elif parsed_doc.get("type") in ["structured_json", "structured_csv"]:
            for rec in parsed_doc.get("records", []):
                ent_id = rec.get("entity_id") or rec.get("id") or f"ENT_{uuid.uuid4().hex[:6]}"
                ent_type = rec.get("entity_type") or rec.get("type") or "UNKNOWN"
                name = rec.get("display_name") or rec.get("name") or ent_id
                entities_map[ent_id] = ExtractedEntity(
                    id=ent_id,
                    type=ent_type.upper(),
                    display_name=name,
                    confidence=float(rec.get("confidence", 1.0)),
                    properties=rec,
                    source_type="GENERIC"
                )

        evidence_list.append(ExtractedEvidence(
            type="DOCUMENT",
            description=f"Generic Document Ingestion ({filename}): Parsed {len(entities_map)} entities and {len(relationships)} connections.",
            source_type="GENERIC",
            properties={"filename": filename}
        ))

        return ParsedSourceResult(
            source_type="GENERIC",
            text_summary=f"Processed generic document {filename} with {len(entities_map)} entities.",
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=parsed_doc.get("records", [])
        )

class ParserRegistry:
    """Central registry and factory for all source-specific connectors."""

    _parsers: List[BaseSourceParser] = [
        CDRParser(),
        FinancialTransactionParser(),
        FIRParser(),
        SurveillanceReportParser(),
        SocialMediaParser(),
        CriminalHistoryParser(),
        IntelligenceReportParser()
    ]
    _fallback_parser: BaseSourceParser = GenericDocumentParser()

    @classmethod
    def get_parser(
        cls,
        source_type: Optional[str] = None,
        content: Optional[bytes] = None,
        filename: Optional[str] = None
    ) -> BaseSourceParser:
        """Resolves the appropriate parser by explicit source_type or automated heuristic detection."""
        if source_type and source_type.upper() not in ["AUTO", "GENERIC", ""]:
            target_st = source_type.upper().strip()
            for parser in cls._parsers:
                if parser.source_type_name == target_st:
                    return parser
            logger.warning(f"No specific parser registered for '{source_type}', attempting automated detection.")

        # Heuristic auto-detection
        if content is not None and filename is not None:
            for parser in cls._parsers:
                if parser.can_parse(content, filename):
                    logger.info(f"Auto-detected parser '{parser.source_type_name}' for file '{filename}'.")
                    return parser

        return cls._fallback_parser

    @classmethod
    def list_supported_sources(cls) -> List[str]:
        """Returns list of supported source_type identifiers."""
        return [p.source_type_name for p in cls._parsers] + ["GENERIC"]
