import unittest
from datetime import datetime

from backend.app.services.parsers.registry import ParserRegistry
from backend.app.services.parsers.cdr_parser import CDRParser
from backend.app.services.parsers.financial_parser import FinancialTransactionParser
from backend.app.services.parsers.fir_parser import FIRParser
from backend.app.services.parsers.surveillance_parser import SurveillanceReportParser
from backend.app.services.parsers.social_media_parser import SocialMediaParser
from backend.app.services.parsers.criminal_history_parser import CriminalHistoryParser
from backend.app.services.parsers.intelligence_report_parser import IntelligenceReportParser

class TestSourceParsers(unittest.TestCase):

    def test_registry_supported_sources(self):
        sources = ParserRegistry.list_supported_sources()
        self.assertIn("CDR", sources)
        self.assertIn("FINANCIAL", sources)
        self.assertIn("FIR", sources)
        self.assertIn("SURVEILLANCE", sources)
        self.assertIn("SOCIAL_MEDIA", sources)
        self.assertIn("CRIMINAL_HISTORY", sources)
        self.assertIn("INTELLIGENCE_REPORT", sources)
        self.assertIn("GENERIC", sources)

    def test_cdr_parser_csv(self):
        csv_data = (
            "caller_number,callee_number,caller_name,callee_name,timestamp,duration_sec,call_type,cell_tower_id\n"
            "+919876543210,+919812345678,Arjun Mehta,Sameer Khan,2026-08-15 14:30:00,185,VOICE,TOWER_MUM_04\n"
            "+919876543210,+919899887766,Arjun Mehta,Ravi Sharma,2026-08-15 15:45:00,45,SMS,TOWER_MUM_04\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("CDR", csv_data, "cdr_sample.csv")
        self.assertEqual(parser.source_type_name, "CDR")
        
        result = parser.parse(csv_data, "cdr_sample.csv")
        self.assertEqual(result.source_type, "CDR")
        self.assertGreaterEqual(len(result.entities), 3) # Phones + Persons + Towers
        self.assertGreaterEqual(len(result.relationships), 2)
        self.assertTrue(any(r.type == "CALLED" for r in result.relationships))
        self.assertTrue(any(r.type == "TEXTED" for r in result.relationships))
        self.assertTrue(all(e.source_type == "CDR" for e in result.entities))

    def test_financial_parser_csv(self):
        csv_data = (
            "sender_acc,receiver_acc,sender_name,receiver_name,amount,currency,timestamp,txn_type,bank_name\n"
            "ACC9001,ACC9002,Arjun Mehta,Vikram Das,500000,INR,2026-08-18 10:15:00,RTGS,State Bank of India\n"
            "ACC9002,ACC9003,Vikram Das,Sameer Khan,480000,INR,2026-08-18 11:30:00,IMPS,HDFC Bank\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("FINANCIAL", csv_data, "bank_statement.csv")
        self.assertEqual(parser.source_type_name, "FINANCIAL")

        result = parser.parse(csv_data, "bank_statement.csv")
        self.assertEqual(result.source_type, "FINANCIAL")
        self.assertTrue(any(e.type == "BANK_ACCOUNT" for e in result.entities))
        self.assertTrue(any(r.type == "TRANSFERRED_TO" for r in result.relationships))
        self.assertGreaterEqual(len(result.evidence), 2)

    def test_fir_parser_structured(self):
        csv_data = (
            "fir_number,police_station,complainant,accused,ipc_sections,incident_location,incident_date\n"
            "FIR/2026/108,Central PS,Sunil Varma,Arjun Mehta,IPC 420 120B,Nariman Point Mumbai,2026-08-10\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("FIR", csv_data, "fir_records.csv")
        self.assertEqual(parser.source_type_name, "FIR")

        result = parser.parse(csv_data, "fir_records.csv")
        self.assertEqual(result.source_type, "FIR")
        self.assertTrue(any(e.display_name == "Arjun Mehta" for e in result.entities))
        self.assertTrue(any(e.type == "ORGANIZATION" and "Police Station" in e.display_name for e in result.entities))
        self.assertTrue(any(r.type == "ACCUSED_OF" for r in result.relationships))

    def test_surveillance_parser(self):
        csv_data = (
            "target_person,location,accompanied_by,vehicle_plate,notes,team,timestamp\n"
            "Arjun Mehta,Hotel Marine Plaza,Ravi Sharma,MH01AB1234,Meeting observed in lobby,Bravo Team,2026-08-20 19:30:00\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("SURVEILLANCE", csv_data, "surveillance_log.csv")
        self.assertEqual(parser.source_type_name, "SURVEILLANCE")

        result = parser.parse(csv_data, "surveillance_log.csv")
        self.assertEqual(result.source_type, "SURVEILLANCE")
        self.assertTrue(any(e.type == "VEHICLE" for e in result.entities))
        self.assertTrue(any(r.type == "MET_WITH" for r in result.relationships))
        self.assertTrue(any(r.type == "SPOTTED_AT" for r in result.relationships))

    def test_social_media_parser(self):
        csv_data = (
            "profile_handle,display_name,platform,post_text,mentioned_users,group_name,timestamp\n"
            "@arjun_m,Arjun Mehta,Telegram,Transfer confirmed for next delivery,@ravi_s,Import Channel,2026-08-22 21:00:00\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("SOCIAL_MEDIA", csv_data, "telegram_export.csv")
        self.assertEqual(parser.source_type_name, "SOCIAL_MEDIA")

        result = parser.parse(csv_data, "telegram_export.csv")
        self.assertEqual(result.source_type, "SOCIAL_MEDIA")
        self.assertTrue(any(e.type == "PERSON" and "arjun_m" in e.id for e in result.entities))
        self.assertTrue(any(e.type == "ORGANIZATION" for e in result.entities))
        self.assertTrue(any(r.type == "MEMBER_OF" for r in result.relationships))
        self.assertTrue(any(r.type == "MENTIONED_WITH" for r in result.relationships))

    def test_criminal_history_parser(self):
        csv_data = (
            "person_name,alias,criminal_id,offense_type,ipc_sections,disposition,court,linked_fir_ids,gang_affiliation,arrest_date\n"
            "Arjun Mehta,A.M.,CR-2024-88,Financial Hawala,IPC 420 120B,Bail,Sessions Court Mumbai,FIR-2024-91,Nexus Syndicate,2024-03-15\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("CRIMINAL_HISTORY", csv_data, "criminal_dossier.csv")
        self.assertEqual(parser.source_type_name, "CRIMINAL_HISTORY")

        result = parser.parse(csv_data, "criminal_dossier.csv")
        self.assertEqual(result.source_type, "CRIMINAL_HISTORY")
        person = next((e for e in result.entities if e.type == "PERSON"), None)
        self.assertIsNotNone(person)
        self.assertIn("criminal_history", person.properties)
        self.assertEqual(person.properties["criminal_history"][0]["offense"], "Financial Hawala")
        self.assertTrue(any(r.type == "MEMBER_OF" for r in result.relationships))

    def test_intelligence_report_parser(self):
        txt_data = (
            "INTELLIGENCE BRIEFING: Confidential Informant Report.\n"
            "Subject Arjun Mehta was spotted in Mumbai with Ravi Sharma.\n"
            "Communication recorded on phone +919876543210.\n"
        ).encode("utf-8")

        parser = ParserRegistry.get_parser("INTELLIGENCE_REPORT", txt_data, "intel_briefing_01.txt")
        self.assertEqual(parser.source_type_name, "INTELLIGENCE_REPORT")

        result = parser.parse(txt_data, "intel_briefing_01.txt")
        self.assertEqual(result.source_type, "INTELLIGENCE_REPORT")
        self.assertGreaterEqual(len(result.entities), 2)
        self.assertTrue(all(ev.source_type == "INTELLIGENCE_REPORT" for ev in result.evidence))

if __name__ == "__main__":
    unittest.main()
