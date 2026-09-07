import json
import re
import httpx
import logging
from typing import List, Dict, Any
from backend.app.config import settings

logger = logging.getLogger("relationship_extractor")

class RelationshipExtractor:
    @staticmethod
    def extract_relationships(text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extracts relationships between identified entities in English, Hindi, and mixed police narratives."""
        if len(entities) < 2:
            return []

        # 1. Attempt Ollama multilingual extraction
        try:
            url = f"{settings.OLLAMA_HOST}/api/chat"
            system_prompt = (
                "You are an expert NLP model for criminal network analysis. Extract relationships between the provided entities from English or Hindi text. "
                "Relationship types: CALLED, TEXTED, MET, VISITED, OWNS, USES, WORKS_FOR, ASSOCIATED_WITH, TRANSFERRED_TO, TRAVELED_TO, CONNECTED_TO, INVOLVED_IN, ACCUSED_OF, MEMBER_OF, CONNECTED_ON_SOCIAL. "
                "Output must only connect entities present in the entity list. "
                "Respond STRICTLY in JSON format. Schema:\n"
                '{"relationships": [{"source_entity_id": "P001", "target_entity_id": "P002", "type": "MET", "confidence": 0.9, "timestamp": "2026-08-12T12:00:00", "properties": {"details": "Met at location"}}]}'
            )
            
            entities_str = json.dumps([{ "id": e["id"], "type": e["type"], "display_name": e["display_name"] } for e in entities])
            user_prompt = f"Entities: {entities_str}\n\nText:\n{text}"
            
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "format": "json"
            }
            
            logger.info("Attempting Ollama multilingual relationship extraction...")
            with httpx.Client(timeout=8.0) as client:
                r = client.post(url, json=payload)
                if r.status_code == 200:
                    res_json = r.json()
                    content = res_json.get("message", {}).get("content", "")
                    cleaned_content = RelationshipExtractor._clean_json_string(content)
                    data = json.loads(cleaned_content)
                    if "relationships" in data and isinstance(data["relationships"], list) and len(data["relationships"]) > 0:
                        valid_ids = {e["id"] for e in entities}
                        filtered_rels = []
                        for rel in data["relationships"]:
                            if rel.get("source_entity_id") in valid_ids and rel.get("target_entity_id") in valid_ids:
                                filtered_rels.append(rel)
                        logger.info(f"Ollama successfully extracted {len(filtered_rels)} relationships.")
                        return filtered_rels
        except Exception as e:
            logger.warning(f"Ollama relationship extraction failed or timed out: {e}. Falling back to Multilingual Rule-based extraction.")

        # 2. Fallback: Multilingual Rule-Based / Regex relationship extraction
        return RelationshipExtractor._fallback_rule_extract(text, entities)

    @staticmethod
    def _clean_json_string(content: str) -> str:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    @staticmethod
    def _fallback_rule_extract(text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback method to link entities across English and Hindi sentences."""
        relationships = []
        # Split on English and Devanagari sentence delimiters (।, ., !, ?, \n)
        sentences = re.split(r'[.!?।\n]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Find which entities are present in this sentence
            present_entities = []
            for ent in entities:
                name_esc = re.escape(ent["display_name"])
                id_esc = re.escape(ent["id"])
                # Match either full token, Devanagari word, or ID
                if re.search(r'(?:\b|(?<=[\s,।]))(?:' + name_esc + r'|' + id_esc + r')(?:\b|(?=[\s,।]))', sentence, re.IGNORECASE):
                    present_entities.append(ent)
            
            if len(present_entities) < 2:
                continue
                
            for i in range(len(present_entities)):
                for j in range(i + 1, len(present_entities)):
                    e1 = present_entities[i]
                    e2 = present_entities[j]
                    
                    rel_type = "CONNECTED_TO"
                    confidence = 0.5
                    sent_lower = sentence.lower()
                    
                    # 1. Call / Telecom / Contact keywords (English & Hindi)
                    if re.search(r'(?:called|phoned|contacted|dialed|spoke|messaged|sms|whatsapp|pinged|कॉल किया|फोन किया|बातचीत|संदेश भेजा|मैसेज|संपर्क किया)', sent_lower):
                        if e1["type"] == "PERSON" and e2["type"] == "PHONE":
                            rel_type = "USES"
                            confidence = 0.85
                        elif e1["type"] == "PHONE" and e2["type"] == "PERSON":
                            e1, e2 = e2, e1
                            rel_type = "USES"
                            confidence = 0.85
                        elif e1["type"] == "PERSON" and e2["type"] == "PERSON":
                            rel_type = "CALLED"
                            confidence = 0.8
                        elif e1["type"] == "PHONE" and e2["type"] == "PHONE":
                            rel_type = "CALLED"
                            confidence = 0.85

                    # 2. Meeting / Co-presence / Location keywords (English & Hindi)
                    elif re.search(r'(?:met|meeting|saw|seen|together|visiting|spotted|observed|staying|मुलाकात की|मिले|देखा गया|हाजिर था|मौजूद था|गया|पहुंचा|विजिट किया|निगरानी)', sent_lower):
                        if e1["type"] == "PERSON" and e2["type"] == "PERSON":
                            rel_type = "MET"
                            confidence = 0.85
                        elif e1["type"] == "PERSON" and e2["type"] == "LOCATION":
                            rel_type = "VISITED"
                            confidence = 0.85
                        elif e2["type"] == "PERSON" and e1["type"] == "LOCATION":
                            e1, e2 = e2, e1
                            rel_type = "VISITED"
                            confidence = 0.85

                    # 3. Vehicle keywords (English & Hindi)
                    elif re.search(r'(?:vehicle|car|suv|driving|owns|license|plate|drove|वाहन|गाड़ी|कार|चला रहा था|सवार|ड्राइव)', sent_lower):
                        if e1["type"] == "PERSON" and e2["type"] == "VEHICLE":
                            rel_type = "DRIVING" if "चला" in sent_lower or "drove" in sent_lower or "driving" in sent_lower else "ASSOCIATED_WITH"
                            confidence = 0.8
                        elif e2["type"] == "PERSON" and e1["type"] == "VEHICLE":
                            e1, e2 = e2, e1
                            rel_type = "DRIVING"
                            confidence = 0.8

                    # 4. Financial / Banking keywords (English & Hindi)
                    elif re.search(r'(?:sent|transferred|wire|paid|funds|txn|transaction|rs|inr|account|पैसे भेजे|रकम|ट्रांसफर|भुगतान किया|खाते में|रुपये|खाता)', sent_lower):
                        if e1["type"] == "PERSON" and e2["type"] == "PERSON":
                            rel_type = "TRANSFERRED_TO"
                            confidence = 0.75
                        elif e1["type"] == "BANK_ACCOUNT" or e2["type"] == "BANK_ACCOUNT":
                            rel_type = "TRANSFERRED_TO"
                            confidence = 0.85

                    # 5. Crime / Accused keywords (English & Hindi)
                    elif re.search(r'(?:accused|fir|complaint|involved|crime|arrested|धारा|आरोपी|मामला दर्ज|संलिप्त|शामिल|धोखाधड़ी|चोरी|गिरफ्तार)', sent_lower):
                        if e1["type"] == "PERSON" and e2["type"] == "ORGANIZATION":
                            rel_type = "ACCUSED_OF" if "PS" in e2["id"] or "थाना" in e2["display_name"] else "MEMBER_OF"
                            confidence = 0.85
                        elif e2["type"] == "PERSON" and e1["type"] == "ORGANIZATION":
                            e1, e2 = e2, e1
                            rel_type = "ACCUSED_OF"
                            confidence = 0.85
                        elif e1["type"] == "PERSON" and e2["type"] == "PERSON":
                            rel_type = "ASSOCIATED_WITH"
                            confidence = 0.8

                    relationships.append({
                        "source_entity_id": e1["id"],
                        "target_entity_id": e2["id"],
                        "type": rel_type,
                        "confidence": confidence,
                        "timestamp": None,
                        "properties": {"sentence": sentence}
                    })
                    
        # Remove duplicates
        unique_rels = []
        seen_rels = set()
        for r in relationships:
            key = (r["source_entity_id"], r["target_entity_id"], r["type"])
            if key not in seen_rels:
                seen_rels.add(key)
                unique_rels.append(r)
                
        return unique_rels
