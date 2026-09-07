import unittest
from backend.app.services.entity_extractor import EntityExtractor
from backend.app.services.relationship_extractor import RelationshipExtractor
from backend.app.services.parsers.fir_parser import FIRParser

class TestMultilingualExtraction(unittest.TestCase):

    def test_hindi_entity_extraction_devanagari(self):
        hindi_text = (
            "प्रथम सूचना रिपोर्ट: थाना बांद्रा, मुंबई। "
            "अभियुक्त: अर्जुन मेहता (फोन: ९८७६५४३२१०)। "
            "स्थान: मुंबई। "
            "आरोपी ने पीड़ित से धोखाधड़ी की (धारा ४२०, १२०बी)।"
        )
        
        entities = EntityExtractor.extract_entities(hindi_text)
        self.assertGreaterEqual(len(entities), 2)
        
        # Verify Person entity extracted
        person = next((e for e in entities if e["type"] == "PERSON"), None)
        self.assertIsNotNone(person)
        self.assertIn("अर्जुन", person["display_name"])

        # Verify Location entity extracted
        loc = next((e for e in entities if e["type"] == "LOCATION"), None)
        self.assertIsNotNone(loc)

        # Verify Phone entity extracted
        phone = next((e for e in entities if e["type"] == "PHONE"), None)
        self.assertIsNotNone(phone)

    def test_hindi_relationship_extraction(self):
        hindi_text = (
            "अर्जुन मेहता ने रवि शर्मा से मुंबई में मुलाकात की। "
            "इसके बाद अर्जुन मेहता ने रवि शर्मा को फोन किया।"
        )
        
        entities = [
            {"id": "P001", "type": "PERSON", "display_name": "अर्जुन मेहता"},
            {"id": "P002", "type": "PERSON", "display_name": "रवि शर्मा"},
            {"id": "LOC002", "type": "LOCATION", "display_name": "मुंबई"}
        ]
        
        relationships = RelationshipExtractor.extract_relationships(hindi_text, entities)
        self.assertGreaterEqual(len(relationships), 1)
        
        # Check meeting and phone call relationship types
        rel_types = [r["type"] for r in relationships]
        self.assertTrue("MET" in rel_types or "CALLED" in rel_types or "VISITED" in rel_types)

    def test_hindi_fir_parser(self):
        fir_hindi = (
            "अपराध संख्या: FIR/2026/892\n"
            "थाना: केंद्रीय पुलिस थाना\n"
            "अभियुक्त: अर्जुन मेहता\n"
            "स्थान: मुंबई\n"
            "विवरण: आरोपी ने धारा 420 के तहत धोखाधड़ी की।\n"
        ).encode("utf-8")

        parser = FIRParser()
        result = parser.parse(fir_hindi, "fir_hindi_report.txt")
        self.assertEqual(result.source_type, "FIR")
        self.assertGreaterEqual(len(result.entities), 2)
        self.assertGreaterEqual(len(result.evidence), 1)

if __name__ == "__main__":
    unittest.main()
