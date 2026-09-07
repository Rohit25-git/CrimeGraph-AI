import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestCaseNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides.clear()
        from backend.app.database.postgres import Base, engine, get_db
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        try:
            from backend.app.models.database_models import User
            from backend.app.api.auth import get_password_hash
            user = db.query(User).filter(User.username == "investigator").first()
            if not user:
                admin_user = User(
                    username="investigator",
                    hashed_password=get_password_hash("password"),
                    role="ADMIN"
                )
                db.add(admin_user)
                db.commit()
        finally:
            db.close()

    def setUp(self):
        self.client = TestClient(app)
        # Login as investigator
        res = self.client.post('/api/auth/login', data={'username': 'investigator', 'password': 'password'})
        self.assertEqual(res.status_code, 200)
        self.token = res.json()['access_token']
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_get_investigations_list(self):
        res = self.client.get('/api/investigations', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        invs = res.json()
        self.assertIsInstance(invs, list)
        self.assertGreaterEqual(len(invs), 1)

    def test_case_network_scoped(self):
        res = self.client.get('/api/investigations/INV-2026-001/network?scope=case', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('investigation_id', data)
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertEqual(data['scope'], 'case')
        for node in data['nodes']:
            self.assertTrue(node.get('is_case_entity'))
            self.assertEqual(node.get('hop_distance'), 0)

    def test_case_network_direct_scope(self):
        res = self.client.get('/api/investigations/INV-2026-001/network?scope=direct', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['scope'], 'direct')
        self.assertGreaterEqual(len(data['nodes']), 6)

    def test_case_network_invalid_scope(self):
        res = self.client.get('/api/investigations/INV-2026-001/network?scope=invalid_scope', headers=self.headers)
        self.assertEqual(res.status_code, 422)

    def test_scoped_shortest_path(self):
        res = self.client.get(
            '/api/graph/shortest-path?source=P001&target=P003&investigation_id=INV-2026-001&scope=case',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('nodes', data)
        self.assertIn('edges', data)

if __name__ == '__main__':
    unittest.main()
