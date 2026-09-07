import unittest
import json
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.postgres import Base, get_db
from backend.app.api.auth import get_password_hash
from backend.app.models.database_models import User, Document, Entity, Relationship

# Use a SQLite database for unit tests to keep it fast and isolated
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

class TestIngestionPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Create test users
        db = TestingSessionLocal()
        cls.pwd = get_password_hash("testpassword")
        cls.analyst = User(
            username="analyst_test",
            hashed_password=cls.pwd,
            role="ANALYST"
        )
        cls.viewer = User(
            username="viewer_test",
            hashed_password=cls.pwd,
            role="VIEWER"
        )
        db.add(cls.analyst)
        db.add(cls.viewer)
        db.commit()
        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.pop(get_db, None)

    def get_token(self, username, password):
        r = self.client.post(
            "/api/auth/login",
            data={"username": username, "password": password}
        )
        return r.json().get("access_token")

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "Healthy")

    def test_unauthorized_upload(self):
        # Viewer is read-only, should be forbidden
        token = self.get_token("viewer_test", "testpassword")
        headers = {"Authorization": f"Bearer {token}"}
        
        file_data = {"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
        r = self.client.post("/api/upload", files=file_data, headers=headers)
        self.assertEqual(r.status_code, 403) # Forbidden

    def test_file_size_validation(self):
        token = self.get_token("analyst_test", "testpassword")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload file that is > 10MB
        large_content = b"a" * (11 * 1024 * 1024)
        file_data = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
        r = self.client.post("/api/upload", files=file_data, headers=headers)
        self.assertEqual(r.status_code, 400)
        self.assertIn("exceeds size limit", r.json()["detail"])

    def test_file_extension_validation(self):
        token = self.get_token("analyst_test", "testpassword")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload invalid extension
        file_data = {"file": ("hacker.exe", io.BytesIO(b"executable"), "application/octet-stream")}
        r = self.client.post("/api/upload", files=file_data, headers=headers)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Unsupported file extension", r.json()["detail"])

    def test_txt_ingestion_and_extraction(self):
        token = self.get_token("analyst_test", "testpassword")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Ingest text document containing names
        text_content = "Arjun Mehta met Ravi Sharma at Location A. Arjun drove vehicle V001."
        file_data = {"file": ("report.txt", io.BytesIO(text_content.encode("utf-8")), "text/plain")}
        
        r = self.client.post("/api/upload", files=file_data, headers=headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "PROCESSED")
        
        # Verify entities were extracted from local DB (we can query entities endpoints)
        r_ent = self.client.get("/api/entities", headers=headers)
        self.assertEqual(r_ent.status_code, 200)
        entities = r_ent.json()
        
        # Should have found P001 (Arjun) and P002 (Ravi)
        ids = {e["id"] for e in entities}
        self.assertIn("P001", ids)
        self.assertIn("P002", ids)
        
        # Verify relationships were created
        r_rel = self.client.get("/api/relationships", headers=headers)
        self.assertEqual(r_rel.status_code, 200)
        relationships = r_rel.json()
        self.assertTrue(len(relationships) > 0)

    def test_structured_csv_cdr_ingestion(self):
        token = self.get_token("analyst_test", "testpassword")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Seed CDR CSV
        csv_content = (
            "source_phone,target_phone,timestamp,duration,source_owner,target_owner\n"
            "PH001,PH002,2026-08-12T10:00:00,120,Arjun,Ravi\n"
            "PH002,PH003,2026-08-12T11:00:00,340,Ravi,Sameer\n"
        )
        file_data = {"file": ("calls.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        
        r = self.client.post("/api/upload", files=file_data, headers=headers)
        self.assertEqual(r.status_code, 200)
        
        # Check phone entities created
        r_ent = self.client.get("/api/entities?type=PHONE", headers=headers)
        phones = r_ent.json()
        phone_ids = {p["id"] for p in phones}
        self.assertIn("PH001", phone_ids)
        self.assertIn("PH002", phone_ids)
        self.assertIn("PH003", phone_ids)

if __name__ == "__main__":
    unittest.main()
