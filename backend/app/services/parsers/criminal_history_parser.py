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

logger = logging.getLogger("criminal_history_parser")

class CriminalHistoryParser(BaseSourceParser):
    """Parser for Criminal History Databases, Prior Offense Sheets, and CCTNS Record Exports."""

    @property
    def source_type_name(self) -> str:
        return "CRIMINAL_HISTORY"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["criminal_history", "history_sheet", "prior_offenses", "cctns", "conviction", "dossier"]):
            return True
        try:
            sample = content[:1500].decode("utf-8", errors="ignore").lower()
            keywords = ["history_sheet_no", "cctns_id", "offense_type", "conviction_status", "prior_convictions", "warrant_status", "अपराध_इतिहास"]
            return any(kw in sample for kw in keywords)
        except Exception:
            return False

    def parse(self, content: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedSourceResult:
        text = content.decode("utf-8", errors="ignore")
        entities_map: Dict[str, ExtractedEntity] = {}
        relationships: List[ExtractedRelationship] = []
        evidence_list: List[ExtractedEvidence] = []
        records: List[Dict[str, Any]] = []

        if filename.lower().endswith(".json"):
            try:
                data = json.loads(text)
                records = data if isinstance(data, list) else [data]
            except Exception as e:
                logger.warning(f"Failed to parse Criminal History JSON: {e}")
        else:
            try:
                reader = csv.DictReader(io.StringIO(text))
                records = [row for row in reader]
            except Exception as e:
                logger.warning(f"Failed to parse Criminal History CSV: {e}")

        for row in records:
            norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}

            name = (norm_row.get("person_name") or norm_row.get("name") or 
                    norm_row.get("subject_name") or norm_row.get("accused_name") or "")

            if not name:
                continue

            person_id = norm_row.get("entity_id") or f"P_{name.replace(' ', '_')}"
            alias = norm_row.get("alias") or norm_row.get("aliases") or norm_row.get("known_as") or ""
            criminal_id = norm_row.get("criminal_id") or norm_row.get("cctns_id") or norm_row.get("history_sheet_no") or f"CR_{uuid.uuid4().hex[:6]}"
            offense = norm_row.get("offense_type") or norm_row.get("crime_type") or norm_row.get("offense") or "Unspecified Offense"
            sections = norm_row.get("ipc_sections") or norm_row.get("bns_sections") or norm_row.get("acts") or ""
            disposition = norm_row.get("disposition") or norm_row.get("status") or norm_row.get("conviction_status") or "Under Trial"
            jurisdiction = norm_row.get("court") or norm_row.get("jurisdiction") or norm_row.get("police_station") or "State Jurisdiction"
            case_no = norm_row.get("linked_fir_ids") or norm_row.get("case_numbers") or norm_row.get("case_no") or "Case Reference"
            mo = norm_row.get("modus_operandi") or norm_row.get("mo") or ""
            gang = norm_row.get("gang_affiliation") or norm_row.get("syndicate") or ""

            ts_str = norm_row.get("arrest_date") or norm_row.get("date") or norm_row.get("year") or ""
            ts = None
            if ts_str:
                for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%Y"):
                    try:
                        ts = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        pass
            if not ts:
                ts = datetime.utcnow()

            # Structured criminal history record item
            history_item = {
                "record_id": criminal_id,
                "offense": offense,
                "sections": sections,
                "disposition": disposition,
                "case_number": case_no,
                "jurisdiction": jurisdiction,
                "date": ts.strftime("%Y-%m-%d"),
                "modus_operandi": mo
            }

            # 1. Person Entity with criminal history array in properties
            if person_id not in entities_map:
                entities_map[person_id] = ExtractedEntity(
                    id=person_id,
                    type="PERSON",
                    display_name=f"{name}" + (f" (alias {alias})" if alias else ""),
                    confidence=1.0,
                    properties={
                        "alias": alias,
                        "cctns_id": criminal_id,
                        "criminal_history": [history_item]
                    },
                    source_type="CRIMINAL_HISTORY"
                )
            else:
                # Append to existing criminal history list
                existing_hist = entities_map[person_id].properties.setdefault("criminal_history", [])
                existing_hist.append(history_item)

            # 2. Gang Affiliation Organization Entity
            if gang:
                gang_id = f"ORG_GANG_{gang.replace(' ', '_')}"
                if gang_id not in entities_map:
                    entities_map[gang_id] = ExtractedEntity(
                        id=gang_id,
                        type="ORGANIZATION",
                        display_name=f"{gang} Syndicate",
                        confidence=0.9,
                        properties={"category": "Organized Crime Syndicate"},
                        source_type="CRIMINAL_HISTORY"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=person_id,
                    target_entity_id=gang_id,
                    type="MEMBER_OF",
                    timestamp=ts,
                    confidence=0.9,
                    properties={"role": "Identified Associate"},
                    source_type="CRIMINAL_HISTORY",
                    id=str(uuid.uuid4())
                ))

            # 3. Evidence Entry
            evidence_list.append(ExtractedEvidence(
                type="CRIMINAL_HISTORY",
                description=f"Official Criminal History record ({criminal_id}): {name} registered for {offense} ({sections}) under {jurisdiction}. Status: {disposition}.",
                source_type="CRIMINAL_HISTORY",
                entity_id=person_id,
                properties={"cctns_id": criminal_id, "offense": offense, "disposition": disposition}
            ))

        summary = f"Criminal History database parsed from {filename}: {len(entities_map)} individuals mapped with prior conviction/case records."
        return ParsedSourceResult(
            source_type="CRIMINAL_HISTORY",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
