import os
import sys

# Redirect to seed_database.py since it seeds both structured data (Postgres) and the relationship graph (Neo4j)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from scripts.seed_database import seed_db

if __name__ == "__main__":
    print("Initiating full graph and database seed...")
    seed_db()
