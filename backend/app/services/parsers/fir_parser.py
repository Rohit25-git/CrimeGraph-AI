import csv
import io
import json
import logging
import re
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

logger = logging.getLogger("fir_parser")

class FIRParser(BaseSourceParser):
    """Parser for First Information Reports (FIRs) & Police Crime Case Records."""

    @property
    def source_type_name(self) -> str:
        return "FIR"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["fir", "police_report", "crime_report", "case_diary", "chargesheet"]):
            return True
        try:
            sample = content[:1500].decode("utf-8", errors="ignore").lower()
            keywords = ["first information report", "police station", "ipc section", "bns section", "complainant", "accused", "fir no", "प्रथम सूचना रिपोर्ट", "थाना"]
            return any(kw in sample for kw in keywords)
        except Exception:
            return False

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        text = content.decode("utf-8", errors="ignore")
        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []
        records: List[Dict[str, Any]] = []

        is_structured = False

        # Attempt structured parse first
        if filename.lower().endswith(".json"):
            try:
                data = json.loads(text)
                records = data if isinstance(data, list) else [data]
                is_structured = True
            except Exception:
                pass
        elif filename.lower().endswith(".csv"):
            try:
                reader = csv.DictReader(io.StringIO(text))
                records = [row for row in reader]
                if records and any("fir" in k.lower() or "accused" in k.lower() or "station" in k.lower() for k in records[0].keys()):
                    is_structured = True
            except Exception:
                pass

        if is_structured:
            for row in records:
                norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}
                
                fir_no = norm_row.get("fir_number") or norm_row.get("fir_no") or norm_row.get("crime_no") or f"FIR_{uuid.uuid4().hex[:6]}"
                ps_name = norm_row.get("police_station") or norm_row.get("ps") or norm_row.get("station_name") or "Central PS"
                complainant = norm_row.get("complainant") or norm_row.get("informant") or ""
                accused_raw = norm_row.get("accused") or norm_row.get("suspect") or norm_row.get("named_accused") or ""
                sections = norm_row.get("ipc_sections") or norm_row.get("bns_sections") or norm_row.get("sections") or ""
                location = norm_row.get("incident_location") or norm_row.get("place_of_occurrence") or norm_row.get("location") or ""
                
                ts_str = norm_row.get("date_of_occurrence") or norm_row.get("incident_date") or norm_row.get("fir_date") or ""
                ts = None
                if ts_str:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            ts = datetime.strptime(ts_str, fmt)
                            break
                        except ValueError:
                            pass
                if not ts:
                    ts = datetime.utcnow()

                # 1. Police Station Org Entity
                ps_id = f"ORG_PS_{ps_name.replace(' ', '_')}"
                if ps_id not in entities_map:
                    entities_map[ps_id] = ExtractedEntity(
                        id=ps_id,
                        type="ORGANIZATION",
                        display_name=f"Police Station {ps_name}",
                        confidence=1.0,
                        properties={"jurisdiction": ps_name, "category": "Law Enforcement"},
                        source_type="FIR"
                    )

                # 2. Incident Location Entity
                if location:
                    loc_id = f"LOC_{location.replace(' ', '_')}"
                    if loc_id not in entities_map:
                        entities_map[loc_id] = ExtractedEntity(
                            id=loc_id,
                            type="LOCATION",
                            display_name=location,
                            confidence=0.9,
                            properties={"fir_ref": fir_no},
                            source_type="FIR"
                        )

                # 3. Complainant Entity
                if complainant:
                    comp_id = f"P_{complainant.replace(' ', '_')}"
                    if comp_id not in entities_map:
                        entities_map[comp_id] = ExtractedEntity(
                            id=comp_id,
                            type="PERSON",
                            display_name=complainant,
                            confidence=0.95,
                            properties={"role": "COMPLAINANT", "fir_number": fir_no},
                            source_type="FIR"
                        )
                    # Filed At relationship
                    relationships.append(ExtractedRelationship(
                        source_entity_id=comp_id,
                        target_entity_id=ps_id,
                        type="FILED_AT",
                        timestamp=ts,
                        confidence=0.95,
                        properties={"fir_number": fir_no, "sections": sections},
                        source_type="FIR",
                        id=str(uuid.uuid4())
                    ))

                # 4. Accused Entities (split if multiple)
                accused_list = [a.strip() for a in re.split(r'[,;&|]', accused_raw) if a.strip()]
                accused_entity_ids = []
                for acc_name in accused_list:
                    acc_id = f"P_{acc_name.replace(' ', '_')}"
                    accused_entity_ids.append(acc_id)
                    if acc_id not in entities_map:
                        entities_map[acc_id] = ExtractedEntity(
                            id=acc_id,
                            type="PERSON",
                            display_name=acc_name,
                            confidence=0.95,
                            properties={"role": "ACCUSED", "fir_number": fir_no, "ipc_sections": sections},
                            source_type="FIR"
                        )
                    # Relationship to Police Station / FIR
                    rel_id = str(uuid.uuid4())
                    relationships.append(ExtractedRelationship(
                        source_entity_id=acc_id,
                        target_entity_id=ps_id,
                        type="ACCUSED_OF",
                        timestamp=ts,
                        confidence=0.95,
                        properties={"fir_number": fir_no, "sections": sections},
                        source_type="FIR",
                        id=rel_id
                    ))

                    if location:
                        relationships.append(ExtractedRelationship(
                            source_entity_id=acc_id,
                            target_entity_id=f"LOC_{location.replace(' ', '_')}",
                            type="INVOLVED_IN",
                            timestamp=ts,
                            confidence=0.85,
                            properties={"incident_location": location},
                            source_type="FIR",
                            id=str(uuid.uuid4())
                        ))

                    # Evidence
                    evidence_list.append(ExtractedEvidence(
                        type="FIR",
                        description=f"FIR No. {fir_no} registered at PS {ps_name}: Subject {acc_name} named under sections {sections or 'N/A'}.",
                        source_type="FIR",
                        entity_id=acc_id,
                        relationship_id=rel_id,
                        properties={"fir_number": fir_no, "sections": sections, "ps": ps_name}
                    ))

                # Co-accused relationships between multiple accused
                for i in range(len(accused_entity_ids)):
                    for j in range(i + 1, len(accused_entity_ids)):
                        relationships.append(ExtractedRelationship(
                            source_entity_id=accused_entity_ids[i],
                            target_entity_id=accused_entity_ids[j],
                            type="ASSOCIATED_WITH",
                            timestamp=ts,
                            confidence=0.9,
                            properties={"co_accused_in_fir": fir_no},
                            source_type="FIR",
                            id=str(uuid.uuid4())
                        ))

        else:
            # Narrative FIR parser using Regex pattern matching and EntityExtractor
            nlp_entities = EntityExtractor.extract_entities(text)
            for ne in nlp_entities:
                entities_map[ne["id"]] = ExtractedEntity(
                    id=ne["id"],
                    type=ne["type"],
                    display_name=ne["display_name"],
                    confidence=ne.get("confidence", 0.9),
                    properties=ne.get("properties", {}),
                    source_type="FIR"
                )

            # Match IPC sections from text
            ipc_matches = re.findall(r'(?:IPC|BNS|Section|धारा)\s*([0-9A-Za-z,\s/]+)', text, re.IGNORECASE)
            sections_str = ", ".join([m.strip() for m in ipc_matches[:3]]) if ipc_matches else "IPC Sections"

            # Match FIR number
            fir_match = re.search(r'(?:FIR\s*(?:No\.?|Number)?|अपराध\s*संख्या)\s*[:#]?\s*([0-9A-Za-z/_-]+)', text, re.IGNORECASE)
            fir_no = fir_match.group(1) if fir_match else f"FIR_{uuid.uuid4().hex[:6]}"

            # Add evidence
            for ent_id, ent in entities_map.items():
                evidence_list.append(ExtractedEvidence(
                    type="FIR",
                    description=f"Police case file {fir_no}: Identified entity {ent.display_name} ({ent.type}) in incident record citing {sections_str}.",
                    source_type="FIR",
                    entity_id=ent_id,
                    properties={"fir_number": fir_no, "sections": sections_str}
                ))

            # Connect co-mentioned persons
            person_ids = [e.id for e in entities_map.values() if e.type == "PERSON"]
            for i in range(len(person_ids)):
                for j in range(i + 1, len(person_ids)):
                    relationships.append(ExtractedRelationship(
                        source_entity_id=person_ids[i],
                        target_entity_id=person_ids[j],
                        type="INVOLVED_IN",
                        timestamp=datetime.utcnow(),
                        confidence=0.85,
                        properties={"fir_number": fir_no, "sections": sections_str},
                        source_type="FIR",
                        id=str(uuid.uuid4())
                    ))

        summary = f"Police FIR records parsed from {filename}: {len(entities_map)} entities, {len(relationships)} relationships, {len(evidence_list)} evidence citations logged."
        return ParsedSourceResult(
            source_type="FIR",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
