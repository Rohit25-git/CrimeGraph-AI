import json
import re
import httpx
import logging
from typing import List, Dict, Any
from backend.app.config import settings

logger = logging.getLogger("entity_extractor")

class EntityExtractor:
    @staticmethod
    def extract_entities(text: str) -> List[Dict[str, Any]]:
        """Extracts entities from English, Hindi, and multilingual police text. Attempts Ollama first, falls back to Rules."""
        # 1. Attempt local Ollama extraction with multilingual prompt
        try:
            url = f"{settings.OLLAMA_HOST}/api/chat"
            system_prompt = (
                "You are an expert multilingual NLP model for Indian criminal network analysis. "
                "Extract named entities from the text, supporting English, Hindi (Devanagari script), and mixed Hinglish. "
                "Entity types: PERSON, PHONE, VEHICLE, LOCATION, ORGANIZATION, BANK_ACCOUNT. "
                "Translate or normalize entity display names appropriately (e.g., 'अर्जुन मेहता' -> display_name: 'Arjun Mehta' / 'अर्जुन मेहता', 'मुंबई' -> display_name: 'Mumbai'). "
                "Assign an entity ID if visible (e.g., P001, PH001, V001, LOC001, ORG001, ACC001). "
                "If not visible, generate unique IDs with prefixes: P_ for Person, PH_ for Phone, V_ for Vehicle, LOC_ for Location, ORG_ for Org, ACC_ for Account. "
                "Extract criminal attributes like IPC/BNS sections (e.g. 420, 120B) or role into properties. "
                "Respond STRICTLY in JSON format without markdown blocks. Schema:\n"
                '{"entities": [{"id": "P001", "type": "PERSON", "display_name": "Arjun Mehta", "confidence": 0.95, "properties": {"role": "Accused", "ipc_sections": "420, 120B"}}]}'
            )
            
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract entities from:\n{text}"}
                ],
                "stream": False,
                "format": "json"
            }
            
            logger.info(f"Attempting Ollama multilingual entity extraction using {settings.OLLAMA_MODEL}...")
            with httpx.Client(timeout=8.0) as client:
                r = client.post(url, json=payload)
                if r.status_code == 200:
                    res_json = r.json()
                    content = res_json.get("message", {}).get("content", "")
                    cleaned_content = EntityExtractor._clean_json_string(content)
                    data = json.loads(cleaned_content)
                    if "entities" in data and isinstance(data["entities"], list) and len(data["entities"]) > 0:
                        logger.info(f"Ollama successfully extracted {len(data['entities'])} multilingual entities.")
                        return data["entities"]
        except Exception as e:
            logger.warning(f"Ollama entity extraction failed or timed out: {e}. Falling back to Multilingual Rule-based extraction.")

        # 2. Fallback: Multilingual Rule-Based / Regex Extraction
        return EntityExtractor._fallback_regex_extract(text)

    @staticmethod
    def _clean_json_string(content: str) -> str:
        """Helper to strip markdown tags if the LLM output contains them."""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    @staticmethod
    def _convert_devanagari_digits(text: str) -> str:
        """Converts Devanagari numerals (०-९) to standard Arabic digits (0-9)."""
        devanagari_digits = "०१२३४५६७८९"
        trans_table = str.maketrans(devanagari_digits, "0123456789")
        return text.translate(trans_table)

    @staticmethod
    def _fallback_regex_extract(text: str) -> List[Dict[str, Any]]:
        """Multilingual regex & dictionary-based entity extractor (English + Hindi Devanagari)."""
        entities = []
        normalized_text = EntityExtractor._convert_devanagari_digits(text)
        
        # Multilingual known entity mappings
        known_persons = {
            "Arjun Mehta": "P001", "Arjun": "P001", "अर्जुन मेहता": "P001", "अर्जुन": "P001",
            "Ravi Sharma": "P002", "Ravi": "P002", "रवि शर्मा": "P002", "रवि": "P002",
            "Sameer Khan": "P003", "Sameer": "P003", "समीर खान": "P003", "समीर": "P003",
            "Vikram Das": "P004", "Vikram": "P004", "विक्रम दास": "P004", "विक्रम": "P004",
            "Priya Nair": "P005", "प्रिया नायर": "P005", "प्रिया": "P005",
            "Amit Patel": "P006", "अमित पटेल": "P006", "अमित": "P006",
            "Rajesh Gupta": "P007", "राजेश गुप्ता": "P007", "राजेश": "P007"
        }
        known_locations = {
            "Location A": "LOC001", "Mumbai": "LOC002", "मुंबई": "LOC002",
            "Delhi": "LOC003", "दिल्ली": "LOC003", "Goa": "LOC004", "गोवा": "LOC004",
            "Pune": "LOC005", "पुणे": "LOC005", "Lucknow": "LOC006", "लखनऊ": "LOC006",
            "Bengaluru": "LOC007", "बेंगलुरु": "LOC007", "Kolkata": "LOC008", "कोलकाता": "LOC008"
        }
        known_orgs = {
            "Mehta Exports": "ORG001", "मेहता एक्सपोर्ट्स": "ORG001",
            "Sharma Logistics": "ORG002", "शर्मा लॉजिस्टिक्स": "ORG002",
            "Khan FinCorp": "ORG003", "खान फिनकॉर्प": "ORG003",
            "Central Police Station": "ORG_PS_Central", "केंद्रीय पुलिस थाना": "ORG_PS_Central",
            "Cyber Cell": "ORG_CYBER", "साइबर सेल": "ORG_CYBER"
        }

        # 1. Match Phone Numbers (Standard & with Hindi markers)
        phone_matches = re.finditer(r'(?:(?:फोन|मोबाइल|दूरभाष|phone|mobile|call)\s*[:\-]?\s*)?\b(PH\d{3}|\+?\d{10,12})\b', normalized_text, re.IGNORECASE)
        for i, match in enumerate(phone_matches):
            val = match.group(1)
            ent_id = val if val.startswith("PH") else f"PH_{val.replace('+', '').replace('-', '')}"
            entities.append({
                "id": ent_id,
                "type": "PHONE",
                "display_name": val,
                "confidence": 0.9,
                "properties": {"raw_number": val}
            })

        # 2. Match Vehicles (English & Hindi plate formats)
        vehicle_matches = re.finditer(r'(?:(?:वाहन|गाड़ी|कार|vehicle|car)\s*[:\-]?\s*)?\b(V\d{3}|[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4})\b', normalized_text, re.IGNORECASE)
        for i, match in enumerate(vehicle_matches):
            val = match.group(1)
            ent_id = val if val.startswith("V") else f"V_{val.replace(' ', '').replace('-', '')}"
            entities.append({
                "id": ent_id,
                "type": "VEHICLE",
                "display_name": val,
                "confidence": 0.85,
                "properties": {"plate_number": val}
            })

        # 3. Match Bank Accounts
        acc_matches = re.finditer(r'(?:(?:खाता|अकाउंट|account|acc)\s*[:\-]?\s*)?\b(ACC\d{3}|\d{9,16})\b', normalized_text, re.IGNORECASE)
        for i, match in enumerate(acc_matches):
            val = match.group(1)
            ent_id = val if val.startswith("ACC") else f"ACC_{val}"
            entities.append({
                "id": ent_id,
                "type": "BANK_ACCOUNT",
                "display_name": f"Account {val}",
                "confidence": 0.85,
                "properties": {"account_no": val}
            })

        # 4. Match Known People (English + Devanagari)
        for name, pid in known_persons.items():
            if re.search(r'(?:\b|(?<=[\s,।]))' + re.escape(name) + r'(?:\b|(?=[\s,।]))', text, re.IGNORECASE):
                if not any(e["id"] == pid for e in entities):
                    entities.append({
                        "id": pid,
                        "type": "PERSON",
                        "display_name": name,
                        "confidence": 0.95,
                        "properties": {"matched_token": name}
                    })

        # 5. Match Known Locations (English + Devanagari)
        for loc, lid in known_locations.items():
            if re.search(r'(?:\b|(?<=[\s,।]))' + re.escape(loc) + r'(?:\b|(?=[\s,।]))', text, re.IGNORECASE):
                if not any(e["id"] == lid for e in entities):
                    entities.append({
                        "id": lid,
                        "type": "LOCATION",
                        "display_name": loc,
                        "confidence": 0.95,
                        "properties": {}
                    })

        # 6. Match Known Organizations (English + Devanagari)
        for org, oid in known_orgs.items():
            if re.search(r'(?:\b|(?<=[\s,।]))' + re.escape(org) + r'(?:\b|(?=[\s,।]))', text, re.IGNORECASE):
                if not any(e["id"] == oid for e in entities):
                    entities.append({
                        "id": oid,
                        "type": "ORGANIZATION",
                        "display_name": org,
                        "confidence": 0.95,
                        "properties": {}
                    })

        # 7. Generic Devanagari Accused / Complainant entity regex extraction
        hindi_accused_matches = re.finditer(r'(?:अभियुक्त|आरोपी|संदिग्ध|शिकायतकर्ता|पीड़ित)\s*[:\-]\s*([^\s,;।\n]+(?:\s+[^\s,;।\n]+)?)', text)
        for i, match in enumerate(hindi_accused_matches):
            raw_name = match.group(1).strip()
            if raw_name and len(raw_name) > 2 and not any(e["display_name"] == raw_name for e in entities):
                ent_id = f"P_HI_{i+1}_{raw_name.replace(' ', '_')}"
                entities.append({
                    "id": ent_id,
                    "type": "PERSON",
                    "display_name": raw_name,
                    "confidence": 0.85,
                    "properties": {"role": "Accused/Complainant", "source_language": "Hindi"}
                })

        # 8. Generic Devanagari Location regex extraction
        hindi_loc_matches = re.finditer(r'(?:स्थान|घटनास्थल|थाना|शहर)\s*[:\-]\s*([^\s,;।\n]+(?:\s+[^\s,;।\n]+)?)', text)
        for i, match in enumerate(hindi_loc_matches):
            raw_loc = match.group(1).strip()
            if raw_loc and len(raw_loc) > 2 and not any(e["display_name"] == raw_loc for e in entities):
                loc_id = f"LOC_HI_{i+1}_{raw_loc.replace(' ', '_')}"
                entities.append({
                    "id": loc_id,
                    "type": "LOCATION",
                    "display_name": raw_loc,
                    "confidence": 0.85,
                    "properties": {"source_language": "Hindi"}
                })

        # Ensure uniqueness
        unique_entities = []
        seen_ids = set()
        for ent in entities:
            if ent["id"] not in seen_ids:
                seen_ids.add(ent["id"])
                unique_entities.append(ent)

        return unique_entities
