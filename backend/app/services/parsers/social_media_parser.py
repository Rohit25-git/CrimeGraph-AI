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

logger = logging.getLogger("social_media_parser")

class SocialMediaParser(BaseSourceParser):
    """Parser for Investigator-Uploaded Social Media Exports (Twitter/X, Telegram, WhatsApp, Instagram, Facebook)."""

    @property
    def source_type_name(self) -> str:
        return "SOCIAL_MEDIA"

    def can_parse(self, content: bytes, filename: str) -> bool:
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ["social", "twitter", "telegram", "whatsapp", "instagram", "facebook", "osint", "chat_export"]):
            return True
        try:
            sample = content[:1500].decode("utf-8", errors="ignore").lower()
            keywords = ["profile_handle", "username", "mentioned_users", "channel_name", "post_text", "retweet", "telegram_id", "follower"]
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
                logger.warning(f"Failed to parse Social Media JSON: {e}")
        else:
            try:
                reader = csv.DictReader(io.StringIO(text))
                records = [row for row in reader]
            except Exception as e:
                logger.warning(f"Failed to parse Social Media CSV: {e}")

        for row in records:
            norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items() if k and v is not None}

            handle = (norm_row.get("profile_handle") or norm_row.get("username") or 
                      norm_row.get("author") or norm_row.get("user_id") or norm_row.get("handle") or "")

            display_name = norm_row.get("profile_name") or norm_row.get("display_name") or norm_row.get("real_name") or handle
            platform = norm_row.get("platform") or norm_row.get("source_app") or "Social Media"
            post_text = norm_row.get("post_text") or norm_row.get("message") or norm_row.get("content") or ""
            mentions_raw = norm_row.get("mentioned_users") or norm_row.get("mentions") or norm_row.get("tagged_users") or norm_row.get("replied_to") or ""
            group_name = norm_row.get("group_name") or norm_row.get("channel_name") or norm_row.get("channel") or norm_row.get("page_name") or ""
            location_raw = norm_row.get("geotag") or norm_row.get("location") or ""
            phone_raw = norm_row.get("phone") or norm_row.get("phone_number") or ""

            ts_str = norm_row.get("timestamp") or norm_row.get("post_date") or norm_row.get("created_at") or ""
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

            if not handle:
                continue

            # 1. Profile Owner Person Entity
            user_id = f"P_SOC_{handle.replace('@', '').replace(' ', '_')}"
            if user_id not in entities_map:
                entities_map[user_id] = ExtractedEntity(
                    id=user_id,
                    type="PERSON",
                    display_name=f"{display_name} (@{handle.replace('@', '')})",
                    confidence=0.85,
                    properties={
                        "handle": handle,
                        "platform": platform,
                        "online_identity": True
                    },
                    source_type="SOCIAL_MEDIA"
                )

            # 2. Linked Phone Entity if available in export
            if phone_raw:
                ph_id = f"PH_{phone_raw.replace('+', '').replace('-', '')}"
                if ph_id not in entities_map:
                    entities_map[ph_id] = ExtractedEntity(
                        id=ph_id,
                        type="PHONE",
                        display_name=phone_raw,
                        confidence=0.9,
                        properties={"linked_profile": handle},
                        source_type="SOCIAL_MEDIA"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=user_id,
                    target_entity_id=ph_id,
                    type="USES",
                    timestamp=ts,
                    confidence=0.9,
                    properties={"platform": platform},
                    source_type="SOCIAL_MEDIA",
                    id=str(uuid.uuid4())
                ))

            # 3. Group / Channel Organization Entity
            if group_name:
                grp_id = f"ORG_GRP_{group_name.replace(' ', '_')}"
                if grp_id not in entities_map:
                    entities_map[grpp_id := grp_id] = ExtractedEntity(
                        id=grp_id,
                        type="ORGANIZATION",
                        display_name=f"{group_name} ({platform} Group)",
                        confidence=0.85,
                        properties={"platform": platform, "category": "Online Group"},
                        source_type="SOCIAL_MEDIA"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=user_id,
                    target_entity_id=grp_id,
                    type="MEMBER_OF",
                    timestamp=ts,
                    confidence=0.85,
                    properties={"platform": platform},
                    source_type="SOCIAL_MEDIA",
                    id=str(uuid.uuid4())
                ))

            # 4. Location Entity if Geotagged
            if location_raw:
                loc_id = f"LOC_{location_raw.replace(' ', '_')}"
                if loc_id not in entities_map:
                    entities_map[loc_id] = ExtractedEntity(
                        id=loc_id,
                        type="LOCATION",
                        display_name=location_raw,
                        confidence=0.8,
                        properties={"geotag_source": platform},
                        source_type="SOCIAL_MEDIA"
                    )
                relationships.append(ExtractedRelationship(
                    source_entity_id=user_id,
                    target_entity_id=loc_id,
                    type="POSTED_AT",
                    timestamp=ts,
                    confidence=0.8,
                    properties={"platform": platform},
                    source_type="SOCIAL_MEDIA",
                    id=str(uuid.uuid4())
                ))

            # 5. Mentioned / Tagged Users
            if mentions_raw:
                mentions = [m.strip().replace('@', '') for m in re.split(r'[,;&|\s]', mentions_raw) if m.strip()]
                for mention_handle in mentions:
                    if not mention_handle:
                        continue
                    m_user_id = f"P_SOC_{mention_handle}"
                    if m_user_id not in entities_map:
                        entities_map[m_user_id] = ExtractedEntity(
                            id=m_user_id,
                            type="PERSON",
                            display_name=f"@{mention_handle}",
                            confidence=0.8,
                            properties={"handle": mention_handle, "platform": platform},
                            source_type="SOCIAL_MEDIA"
                        )
                    rel_id = str(uuid.uuid4())
                    relationships.append(ExtractedRelationship(
                        source_entity_id=user_id,
                        target_entity_id=m_user_id,
                        type="MENTIONED_WITH",
                        timestamp=ts,
                        confidence=0.85,
                        properties={"platform": platform, "post_excerpt": post_text[:100]},
                        source_type="SOCIAL_MEDIA",
                        id=rel_id
                    ))

            # 6. Evidence
            evidence_list.append(ExtractedEvidence(
                type="SOCIAL_MEDIA",
                description=f"Social Media Intelligence ({platform}): Activity recorded for @{handle} on {ts.strftime('%Y-%m-%d')}. Text: {post_text[:120]}...",
                source_type="SOCIAL_MEDIA",
                entity_id=user_id,
                properties={"platform": platform, "handle": handle}
            ))

        summary = f"Social Media intelligence export parsed from {filename}: {len(entities_map)} entities, {len(relationships)} social interactions mapped."
        return ParsedSourceResult(
            source_type="SOCIAL_MEDIA",
            text_summary=summary,
            entities=list(entities_map.values()),
            relationships=relationships,
            evidence=evidence_list,
            raw_records=records
        )
