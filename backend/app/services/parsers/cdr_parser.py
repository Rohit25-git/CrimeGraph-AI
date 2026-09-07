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

logger = logging.getLogger("cdr_parser")

class CDRParser(BaseSourceParser):
    """Parser for Telecom Call Detail Records (CDRs) across CSV, JSON, and tabular formats."""

    @property
    def source_type_name(self) -> str:
        return "CDR"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if "cdr" in fn_lower or "call" in fn_lower or "telecom" in fn_lower:
            return True
        try:
            sample = content[:1024].decode("utf-8", errors="ignore").lower()
            keywords = ["caller", "callee", "msisdn", "calling_no", "called_no", "cell_tower", "cell_id", "duration_sec"]
            return any(kw in sample for kw in keywords)
        except Exception:
            return False

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        text = content.decode("utf-8", errors="ignore")
        records: List[Dict[str, Any]] = []

        if filename.lower().endswith(".json"):
            try:
                data = json.loads(text)
                records = data if isinstance(data, list) else [data]
            except Exception as e:
                logger.warning(f"Failed to parse CDR JSON: {e}")
        else:
            # Parse as CSV
            try:
                reader = csv.DictReader(io.StringIO(text))
                records = [row for row in reader]
            except Exception as e:
                logger.warning(f"Failed to parse CDR CSV: {e}")

        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []

        for row in records:
            # Normalize field names
            norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}

            caller = (norm_row.get("caller_number") or norm_row.get("caller_msisdn") or 
                      norm_row.get("calling_no") or norm_row.get("source_phone") or 
                      norm_row.get("caller") or norm_row.get("from_number") or "")
            
            callee = (norm_row.get("callee_number") or norm_row.get("callee_msisdn") or 
                      norm_row.get("called_no") or norm_row.get("target_phone") or 
                      norm_row.get("callee") or norm_row.get("to_number") or "")

            if not caller or not callee:
                continue

            # Format Phone Entity IDs
            caller_id = caller if caller.startswith("PH") else f"PH_{caller.replace('+', '').replace('-', '')}"
            callee_id = callee if callee.startswith("PH") else f"PH_{callee.replace('+', '').replace('-', '')}"

            caller_name = norm_row.get("caller_name") or norm_row.get("source_owner") or ""
            callee_name = norm_row.get("callee_name") or norm_row.get("target_owner") or ""

            duration_str = norm_row.get("duration") or norm_row.get("duration_sec") or norm_row.get("duration_seconds") or "0"
            try:
                duration = int(float(duration_str))
            except ValueError:
                duration = 0

            call_type = norm_row.get("call_type") or norm_row.get("type") or "VOICE"
            tower_id = norm_row.get("cell_tower_id") or norm_row.get("cell_id") or norm_row.get("tower_location") or ""
            imei = norm_row.get("imei") or ""

            # Timestamp parsing
            ts_str = (norm_row.get("timestamp") or norm_row.get("call_date") or 
                      norm_row.get("datetime") or norm_row.get("call_time") or "")
            ts = None
            if ts_str:
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
                    try:
                        ts = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        pass
            if not ts:
                ts = datetime.utcnow()

            # 1. Caller Phone Entity
            if caller_id not in entities_map:
                entities_map[caller_id] = ExtractedEntity(
                    id=caller_id,
                    type="PHONE",
                    display_name=caller,
                    confidence=1.0,
                    properties={"raw_number": caller, "owner_name": caller_name, "imei": imei},
                    source_type="CDR"
                )
            
            # 2. Callee Phone Entity
            if callee_id not in entities_map:
                entities_map[callee_id] = ExtractedEntity(
                    id=callee_id,
                    type="PHONE",
                    display_name=callee,
                    confidence=1.0,
                    properties={"raw_number": callee, "owner_name": callee_name},
                    source_type="CDR"
                )

            # 3. Person entities if owners are identified
            if caller_name:
                person_caller_id = f"P_{caller_name.replace(' ', '_')}"
                if person_caller_id not in entities_map:
                    entities_map[person_caller_id] = ExtractedEntity(
                        id=person_caller_id,
                        type="PERSON",
                        display_name=caller_name,
                        confidence=0.95,
                        properties={"phone": caller},
                        source_type="CDR"
                    )
                # Link Person to Phone
                relationships.append(ExtractedRelationship(
                    source_entity_id=person_caller_id,
                    target_entity_id=caller_id,
                    type="USES",
                    timestamp=ts,
                    confidence=0.95,
                    properties={"carrier_record": True},
                    source_type="CDR",
                    id=str(uuid.uuid4())
                ))

            if callee_name:
                person_callee_id = f"P_{callee_name.replace(' ', '_')}"
                if person_callee_id not in entities_map:
                    entities_map[person_callee_id] = ExtractedEntity(
                        id=person_callee_id,
                        type="PERSON",
                        display_name=callee_name,
                        confidence=0.95,
                        properties={"phone": callee},
                        source_type="CDR"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=person_callee_id,
                    target_entity_id=callee_id,
                    type="USES",
                    timestamp=ts,
                    confidence=0.95,
                    properties={"carrier_record": True},
                    source_type="CDR",
                    id=str(uuid.uuid4())
                ))

            # 4. Cell Tower / Location Entity if present
            if tower_id:
                loc_id = f"LOC_TOWER_{tower_id.replace(' ', '_')}"
                if loc_id not in entities_map:
                    entities_map[loc_id] = ExtractedEntity(
                        id=loc_id,
                        type="LOCATION",
                        display_name=f"Cell Tower {tower_id}",
                        confidence=0.9,
                        properties={"tower_id": tower_id},
                        source_type="CDR"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=caller_id,
                    target_entity_id=loc_id,
                    type="LOCATED_AT",
                    timestamp=ts,
                    confidence=0.9,
                    properties={"duration_sec": duration},
                    source_type="CDR",
                    id=str(uuid.uuid4())
                ))

            # 5. Relationship between phones
            rel_type = "TEXTED" if "SMS" in call_type.upper() or "MESSAGE" in call_type.upper() else "CALLED"
            rel_id = str(uuid.uuid4())
            relationships.append(ExtractedRelationship(
                source_entity_id=caller_id,
                target_entity_id=callee_id,
                type=rel_type,
                timestamp=ts,
                confidence=1.0,
                properties={
                    "duration_sec": duration,
                    "call_type": call_type,
                    "cell_tower_id": tower_id,
                    "imei": imei
                },
                source_type="CDR",
                id=rel_id
            ))

            # 6. Evidence entry
            evidence_list.append(ExtractedEvidence(
                type="CDR",
                description=f"Telecom record: {caller} {rel_type.lower()} {callee} at {ts.isoformat()} (duration: {duration}s, tower: {tower_id or 'N/A'}).",
                source_type="CDR",
                relationship_id=rel_id,
                properties={"caller": caller, "callee": callee, "duration_sec": duration, "tower": tower_id}
            ))

        summary = f"CDR dataset parsed from {filename}: {len(records)} records, {len(entities_map)} entities, {len(relationships)} relationships extracted."
        return ParsedSourceResult(
            source_type="CDR",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
