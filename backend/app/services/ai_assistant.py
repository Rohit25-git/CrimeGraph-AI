import json
import httpx
import logging
import re
from sqlalchemy.orm import Session
from typing import Dict, Any

from backend.app.config import settings
from backend.app.services.graph_service import GraphService
from backend.app.services.evidence_service import EvidenceService
from backend.app.models.database_models import Entity, Relationship, Alert

logger = logging.getLogger("ai_assistant")


class AIAssistantService:

    @staticmethod
    def answer_question(
        db: Session,
        question: str,
        context_entity_id: str = None
    ) -> Dict[str, Any]:
        """
        Queries database facts and sends only the retrieved facts
        to the Groq LLM to generate an explainable, fact-based answer.

        The database/RAG logic remains local.
        Groq is used only for natural-language reasoning/generation.
        """

        # ============================================================
        # 1. DETECT ENTITY IDs
        # ============================================================

        entity_matches = [
            m.upper()
            for m in re.findall(
                r"\b(P\d{3}|PH\d{3}|V\d{3}|LOC\d{3}|ORG\d{3}|ACC\d{3})\b",
                question,
                re.IGNORECASE
            )
        ]

        if entity_matches and not context_entity_id:
            context_entity_id = entity_matches[0]

        facts = {}
        sources = set()
        evidence_list = []
        suggested_actions = ["[View Network]"]

        # ============================================================
        # 2. GATHER DATABASE FACTS
        # ============================================================

        question_lower = question.lower()

        # ------------------------------------------------------------
        # Intent: Path discovery between two entities
        # ------------------------------------------------------------

        if len(entity_matches) >= 2:

            src = entity_matches[0]
            tgt = entity_matches[1]

            path = GraphService.get_shortest_path(
                db,
                src,
                tgt
            )

            facts["shortest_path_analysis"] = {
                "source": src,
                "target": tgt,
                "path_found": len(path.get("nodes", [])) > 0,
                "path": path
            }

            suggested_actions.append("[Find Path]")

        # ------------------------------------------------------------
        # Intent: Timeline / activity analysis
        # ------------------------------------------------------------

        if "timeline" in question_lower or "activity" in question_lower:

            if context_entity_id:

                rels = (
                    db.query(Relationship)
                    .filter(
                        (Relationship.source_entity_id == context_entity_id)
                        |
                        (Relationship.target_entity_id == context_entity_id)
                    )
                    .order_by(Relationship.timestamp.asc())
                    .all()
                )

                facts["chronological_timeline"] = [
                    {
                        "timestamp": (
                            r.timestamp.isoformat()
                            if r.timestamp
                            else "N/A"
                        ),
                        "description": (
                            f"{r.source_entity_id} "
                            f"({r.type}) "
                            f"{r.target_entity_id}"
                        ),
                        "relationship_id": r.id,
                        "metadata": r.metadata_json
                    }
                    for r in rels
                    if r.timestamp
                ]

                suggested_actions.append("[Open Timeline]")

        # ------------------------------------------------------------
        # Intent: Anomaly analysis
        # ------------------------------------------------------------

        if (
            "anomaly" in question_lower
            or "unusual" in question_lower
            or "flagged" in question_lower
        ):

            alerts_query = db.query(Alert)

            if context_entity_id:
                alerts_query = alerts_query.filter(
                    Alert.entity_id == context_entity_id
                )

            alerts = alerts_query.limit(5).all()

            facts["detected_anomalies"] = [
                {
                    "alert_id": a.id,
                    "title": a.title,
                    "severity": a.severity,
                    "reason": a.reason,
                    "status": a.status,
                    "timestamp": (
                        a.timestamp.isoformat()
                        if a.timestamp
                        else "N/A"
                    )
                }
                for a in alerts
            ]

            suggested_actions.append("[View Anomaly]")

        # ------------------------------------------------------------
        # Intent: Bridges / communities
        # ------------------------------------------------------------

        if (
            "bridge" in question_lower
            or "community" in question_lower
            or "communities" in question_lower
        ):

            bridges = GraphService.find_bridges(db)

            facts["structural_bridges"] = bridges[:5]

            suggested_actions.append("[Highlight Community]")

        # ============================================================
        # 3. ENTITY CONTEXT
        # ============================================================

        if context_entity_id:

            entity = (
                db.query(Entity)
                .filter(Entity.id == context_entity_id)
                .first()
            )

            if entity:

                # ----------------------------------------------------
                # Entity details
                # ----------------------------------------------------

                facts["focused_entity"] = {
                    "id": entity.id,
                    "type": entity.type,
                    "display_name": entity.display_name,
                    "metadata": entity.metadata_json
                }

                # ----------------------------------------------------
                # Entity neighborhood
                # ----------------------------------------------------

                neighborhood = GraphService.get_neighborhood(
                    db,
                    context_entity_id,
                    depth=1
                )

                facts["focused_connections"] = []

                for node in neighborhood["nodes"]:

                    if node["id"] != context_entity_id:

                        facts["focused_connections"].append(
                            {
                                "id": node["id"],
                                "type": node["type"],
                                "display_name": node["display_name"]
                            }
                        )

                # ----------------------------------------------------
                # Relationships
                # ----------------------------------------------------

                facts["focused_relationships"] = []

                for edge in neighborhood["edges"]:

                    facts["focused_relationships"].append(
                        {
                            "id": edge["id"],
                            "source": edge["source"],
                            "target": edge["target"],
                            "type": edge["type"],
                            "properties": edge["properties"]
                        }
                    )

                # ----------------------------------------------------
                # Evidence
                # ----------------------------------------------------

                evs = EvidenceService.get_evidence_for_entity(
                    db,
                    context_entity_id
                )

                for ev in evs:

                    evidence_list.append(
                        {
                            "type": ev["type"],
                            "description": ev["description"]
                        }
                    )

                    if ev.get("source_document_name"):
                        sources.add(
                            ev["source_document_name"]
                        )

        else:

            # ========================================================
            # GENERAL NETWORK ANALYSIS
            # ========================================================

            centralities = GraphService.compute_centrality(db)

            top_influence = sorted(
                centralities.get("pagerank", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            facts["network_influence_ranking"] = [
                {
                    "entity_id": node_id,
                    "score_percent": score
                }
                for node_id, score in top_influence
            ]

        # ============================================================
        # 4. BUILD LLM PROMPT
        # ============================================================

        facts_str = json.dumps(
            facts,
            indent=2,
            default=str
        )

        system_prompt = (
            "You are an investigative assistant Copilot for the "
            "CrimeGraph AI platform. "

            "Your job is to explain connections, relationships, "
            "network patterns, and anomalies based STRICTLY on "
            "the retrieved database records provided to you. "

            "You MUST NOT invent any connection, phone number, "
            "vehicle, transaction, person, organization, location, "
            "date, amount, or name. "

            "You must treat the retrieved database facts as the "
            "only source of truth. "

            "If the records do not contain enough information to "
            "answer the question, you MUST return exactly: "
            "'Insufficient evidence in the current dataset.' "
            "in the 'answer' field. "

            "\n\n"

            "If sufficient evidence exists, structure the "
            "'answer' text using these exact sections:\n\n"

            "FACTS\n"
            "[List objective facts directly supported by the data.]\n\n"

            "ANALYTICAL OBSERVATIONS\n"
            "[Describe patterns or relationships visible in the data.]\n\n"

            "INTERPRETATION\n"
            "[Explain the investigative significance of those patterns.]\n\n"

            "LIMITATIONS\n"
            "[Explain what the available data cannot establish.]\n\n"

            "SOURCES\n"
            "[List filenames or evidence IDs supporting the answer.]\n\n"

            "Cite sources in the answer using markdown brackets, "
            "matching the filename or evidence ID, for example "
            "[intel_report_01.txt] or [CDR-001]. "

            "Never declare a person guilty. "

            "Always use analytical terms such as indicator, "
            "relationship, lead, pattern, risk, and anomaly. "

            "Do not make accusations based solely on network "
            "connectivity. "

            "Respond STRICTLY in valid JSON format. "

            "Do not use markdown code fences around the JSON. "

            "Use this exact schema:\n"

            "{\n"
            '  "answer": "Structured answer text containing the FACTS, ANALYTICAL OBSERVATIONS, INTERPRETATION, LIMITATIONS, and SOURCES sections.",\n'
            '  "key_findings": ["Finding 1 [source]", "Finding 2"],\n'
            '  "evidence": [{"type": "CDR/Transaction/etc", "description": "Specific detail from data [source]"}],\n'
            '  "sources": ["source1.txt", "source2.csv"],\n'
            '  "confidence": "High/Medium/Low",\n'
            '  "important_notes": "This analytical result requires investigator review and verification.",\n'
            '  "suggested_actions": ["[View Network]", "[Show Evidence]"]\n'
            "}"
        )

        user_prompt = (
            "RETRIEVED DATABASE FACTS:\n"
            f"{facts_str}\n\n"
            "QUESTION:\n"
            f"{question}"
        )

        # ============================================================
        # 5. CALL GROQ API
        # ============================================================

        try:

            url = settings.GROQ_API_URL

            payload = {
                "model": settings.GROQ_MODEL,

                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],

                "temperature": 0.1,

                "max_tokens": 2000
            }

            headers = {
                "Authorization": (
                    f"Bearer {settings.GROQ_API_KEY}"
                ),
                "Content-Type": "application/json"
            }

            logger.info(
                "Calling Groq for AI Copilot answer..."
            )

            with httpx.Client(timeout=30.0) as client:

                response = client.post(
                    url,
                    json=payload,
                    headers=headers
                )

                # ----------------------------------------------------
                # Successful response
                # ----------------------------------------------------

                if response.status_code == 200:

                    response_json = response.json()

                    content = (
                        response_json
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    if not content:

                        raise ValueError(
                            "Groq returned an empty response."
                        )

                    # Remove possible ```json ... ``` wrappers
                    content_clean = (
                        AIAssistantService
                        ._clean_json_string(content)
                    )

                    # Parse LLM JSON
                    data = json.loads(content_clean)

                    # ------------------------------------------------
                    # Preserve database-derived sources
                    # ------------------------------------------------

                    if (
                        "sources" not in data
                        or not data["sources"]
                    ):

                        data["sources"] = (
                            list(sources)
                            if sources
                            else ["Database Records"]
                        )

                    # ------------------------------------------------
                    # Preserve database-derived evidence
                    # ------------------------------------------------

                    if (
                        "evidence" not in data
                        or not data["evidence"]
                    ):

                        data["evidence"] = (
                            evidence_list
                            if evidence_list
                            else [
                                {
                                    "type": "Graph",
                                    "description": (
                                        "Connection database records"
                                    )
                                }
                            ]
                        )

                    # ------------------------------------------------
                    # Preserve suggested actions
                    # ------------------------------------------------

                    if (
                        "suggested_actions" not in data
                        or not data["suggested_actions"]
                    ):

                        data["suggested_actions"] = (
                            suggested_actions
                        )

                    # ------------------------------------------------
                    # Ensure expected fields exist
                    # ------------------------------------------------

                    if "answer" not in data:

                        data["answer"] = (
                            "Insufficient evidence in the "
                            "current dataset."
                        )

                    if "key_findings" not in data:

                        data["key_findings"] = []

                    if "confidence" not in data:

                        data["confidence"] = "Medium"

                    if "important_notes" not in data:

                        data["important_notes"] = (
                            "This analytical result requires "
                            "investigator review and verification."
                        )

                    logger.info(
                        "Groq AI Copilot response received successfully."
                    )

                    return data

                # ----------------------------------------------------
                # Groq API error
                # ----------------------------------------------------

                else:

                    logger.error(
                        "Groq API returned HTTP "
                        f"{response.status_code}: "
                        f"{response.text}"
                    )

        # ============================================================
        # 6. JSON PARSING ERROR
        # ============================================================

        except json.JSONDecodeError as e:

            logger.error(
                f"Failed to parse Groq JSON response: {e}"
            )

        # ============================================================
        # 7. GENERAL GROQ ERROR
        # ============================================================

        except Exception as e:

            logger.error(
                f"Groq AI Copilot call failed: {e}"
            )

        # ============================================================
        # 8. DATABASE FALLBACK
        # ============================================================

        connection_count = len(
            facts.get(
                "focused_connections",
                []
            )
        )

        relationship_count = len(
            facts.get(
                "focused_relationships",
                []
            )
        )

        target_name = (
            facts
            .get("focused_entity", {})
            .get("display_name", "Unknown")
            if context_entity_id
            else "General Network"
        )

        return {

            "answer": (
                "I analyzed the available network records around "
                f"the target entity. {connection_count} direct "
                "connections were found in the database. "
                "(Groq service is currently unavailable or slow, "
                "so a structured database fallback answer is "
                "being displayed.)"
            ),

            "key_findings": [

                f"Target Entity: {target_name}",

                (
                    "Direct connections in DB: "
                    f"{connection_count}"
                ),

                (
                    "Active relationships: "
                    f"{relationship_count}"
                )
            ],

            "evidence": (
                evidence_list
                if evidence_list
                else [
                    {
                        "type": "Database Records",
                        "description": (
                            "Queried connection database records"
                        )
                    }
                ]
            ),

            "sources": (
                list(sources)
                if sources
                else ["System DB"]
            ),

            "confidence": "Medium (Database fallback)",

            "important_notes": (
                "Disclaimer: This analytical indicator requires "
                "human review and verification."
            ),

            "suggested_actions": suggested_actions
        }

    # ================================================================
    # CLEAN GROQ JSON RESPONSE
    # ================================================================

    @staticmethod
    def _clean_json_string(content: str) -> str:

        content = content.strip()

        if content.startswith("```json"):

            content = content[7:]

        elif content.startswith("```"):

            content = content[3:]

        if content.endswith("```"):

            content = content[:-3]

        return content.strip()