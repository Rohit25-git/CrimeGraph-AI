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

logger = logging.getLogger("surveillance_parser")

class SurveillanceReportParser(BaseSourceParser):
    """Parser for Physical Surveillance Logs, Field Stakeout Reports, and Movement Tracking Records."""

    @property
    def source_type_name(self) -> str:
        return "SURVEILLANCE"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["surveillance", "stakeout", "field_log", "observation", "tracking", "movement"]):
            return True
        try:
            sample = content[:1500].decode("utf-8", errors="ignore").lower()
            keywords = ["surveillance report", "target observed", "spotted at", "accompanied by", "vehicle plate", "field team", "co-located", "निगरानी"]
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
                if records and any("target" in k.lower() or "spotted" in k.lower() or "vehicle" in k.lower() or "observed" in k.lower() for k in records[0].keys()):
                    is_structured = True
            except Exception:
                pass

        if is_structured:
            for row in records:
                norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}
                
                subject = norm_row.get("target_person") or norm_row.get("observed_person") or norm_row.get("subject") or norm_row.get("target") or ""
                location = norm_row.get("location") or norm_row.get("spotted_at") or norm_row.get("place") or ""
                accompanied_raw = norm_row.get("accompanied_by") or norm_row.get("met_with") or norm_row.get("associates") or ""
                vehicle_raw = norm_row.get("vehicle_plate") or norm_row.get("vehicle") or norm_row.get("car") or ""
                activity = norm_row.get("notes") or norm_row.get("activity_observed") or norm_row.get("details") or "Field Observation"
                team = norm_row.get("team") or norm_row.get("officer") or "Surveillance Unit"

                ts_str = norm_row.get("observation_time") or norm_row.get("timestamp") or norm_row.get("date_time") or ""
                ts = None
                if ts_str:
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"):
                        try:
                            ts = datetime.strptime(ts_str, fmt)
                            break
                        except ValueError:
                            pass
                if not ts:
                    ts = datetime.utcnow()

                if not subject:
                    continue

                # 1. Subject Person Entity
                sub_id = f"P_{subject.replace(' ', '_')}"
                if sub_id not in entities_map:
                    entities_map[sub_id] = ExtractedEntity(
                        id=sub_id,
                        type="PERSON",
                        display_name=subject,
                        confidence=0.95,
                        properties={"surveillance_target": True},
                        source_type="SURVEILLANCE"
                    )

                # 2. Location Entity
                loc_id = None
                if location:
                    loc_id = f"LOC_{location.replace(' ', '_')}"
                    if loc_id not in entities_map:
                        entities_map[loc_id] = ExtractedEntity(
                            id=loc_id,
                            type="LOCATION",
                            display_name=location,
                            confidence=0.95,
                            properties={"category": "Surveillance Sighting"},
                            source_type="SURVEILLANCE"
                        )
                    # Subject visited location
                    relationships.append(ExtractedRelationship(
                        source_entity_id=sub_id,
                        target_entity_id=loc_id,
                        type="SPOTTED_AT",
                        timestamp=ts,
                        confidence=0.95,
                        properties={"activity": activity, "logged_by": team},
                        source_type="SURVEILLANCE",
                        id=str(uuid.uuid4())
                    ))

                # 3. Vehicle Entity
                veh_id = None
                if vehicle_raw:
                    veh_id = f"V_{vehicle_raw.replace(' ', '_').replace('-', '')}"
                    if veh_id not in entities_map:
                        entities_map[veh_id] = ExtractedEntity(
                            id=veh_id,
                            type="VEHICLE",
                            display_name=vehicle_raw,
                            confidence=0.95,
                            properties={"plate_number": vehicle_raw},
                            source_type="SURVEILLANCE"
                        )
                    relationships.append(ExtractedRelationship(
                        source_entity_id=sub_id,
                        target_entity_id=veh_id,
                        type="DRIVING",
                        timestamp=ts,
                        confidence=0.9,
                        properties={"spotted_at": location},
                        source_type="SURVEILLANCE",
                        id=str(uuid.uuid4())
                    ))

                # 4. Associates / Accompanied by
                if accompanied_raw:
                    associates = [a.strip() for a in re.split(r'[,;&|]', accompanied_raw) if a.strip()]
                    for assoc_name in associates:
                        assoc_id = f"P_{assoc_name.replace(' ', '_')}"
                        if assoc_id not in entities_map:
                            entities_map[assoc_id] = ExtractedEntity(
                                id=assoc_id,
                                type="PERSON",
                                display_name=assoc_name,
                                confidence=0.9,
                                properties={"co_located": True},
                                source_type="SURVEILLANCE"
                            )
                        # Meeting / Co-located relation
                        rel_id = str(uuid.uuid4())
                        relationships.append(ExtractedRelationship(
                            source_entity_id=sub_id,
                            target_entity_id=assoc_id,
                            type="MET_WITH",
                            timestamp=ts,
                            confidence=0.95,
                            properties={"location": location, "activity": activity, "spatio_temporal": True},
                            source_type="SURVEILLANCE",
                            id=rel_id
                        ))
                        if loc_id:
                            relationships.append(ExtractedRelationship(
                                source_entity_id=assoc_id,
                                target_entity_id=loc_id,
                                type="SPOTTED_AT",
                                timestamp=ts,
                                confidence=0.9,
                                properties={"with": subject},
                                source_type="SURVEILLANCE",
                                id=str(uuid.uuid4())
                            ))

                # 5. Evidence Log
                evidence_list.append(ExtractedEvidence(
                    type="SURVEILLANCE",
                    description=f"Surveillance Observation by {team} at {ts.strftime('%Y-%m-%d %H:%M')}: {subject} spotted at {location or 'Unknown Location'} ({activity}).",
                    source_type="SURVEILLANCE",
                    entity_id=sub_id,
                    properties={"target": subject, "location": location, "vehicle": vehicle_raw, "activity": activity}
                ))

        else:
            # Narrative Surveillance parsing using EntityExtractor
            nlp_entities = EntityExtractor.extract_entities(text)
            for ne in nlp_entities:
                entities_map[ne["id"]] = ExtractedEntity(
                    id=ne["id"],
                    type=ne["type"],
                    display_name=ne["display_name"],
                    confidence=ne.get("confidence", 0.9),
                    properties=ne.get("properties", {}),
                    source_type="SURVEILLANCE"
                )

            # Link co-mentioned Persons & Locations
            person_ids = [e.id for e in entities_map.values() if e.type == "PERSON"]
            loc_ids = [e.id for e in entities_map.values() if e.type == "LOCATION"]

            for pid in person_ids:
                for lid in loc_ids:
                    relationships.append(ExtractedRelationship(
                        source_entity_id=pid,
                        target_entity_id=lid,
                        type="SPOTTED_AT",
                        timestamp=datetime.utcnow(),
                        confidence=0.85,
                        properties={"source": "Surveillance Field Text"},
                        source_type="SURVEILLANCE",
                        id=str(uuid.uuid4())
                    ))

            for i in range(len(person_ids)):
                for j in range(i + 1, len(person_ids)):
                    rel_id = str(uuid.uuid4())
                    relationships.append(ExtractedRelationship(
                        source_entity_id=person_ids[i],
                        target_entity_id=person_ids[j],
                        type="MET_WITH",
                        timestamp=datetime.utcnow(),
                        confidence=0.85,
                        properties={"co_located": True},
                        source_type="SURVEILLANCE",
                        id=rel_id
                    ))

            evidence_list.append(ExtractedEvidence(
                type="SURVEILLANCE",
                description=f"Surveillance Field Report: Extracted {len(person_ids)} persons and {len(loc_ids)} locations from observation narrative.",
                source_type="SURVEILLANCE",
                properties={"entity_count": len(entities_map)}
            ))

        summary = f"Surveillance logs parsed from {filename}: {len(entities_map)} entities, {len(relationships)} co-locations and sightings mapped."
        return ParsedSourceResult(
            source_type="SURVEILLANCE",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
