from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from backend.app.database.postgres import engine, Base, get_db
from backend.app.models.database_models import User
from backend.app.api import auth, upload, entities, relationships, graph, analytics, alerts, assistant, reports, investigations, resolutions, ml
from backend.app.api.auth import get_password_hash
from backend.app.database.neo4j_db import is_neo4j_connected

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

# Auto-create Postgres tables and migrate missing columns
logger.info("Initializing PostgreSQL database schemas...")
Base.metadata.create_all(bind=engine)
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE entities ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.execute(text("ALTER TABLE evidence ADD COLUMN IF NOT EXISTS source_type VARCHAR(100) DEFAULT 'GENERIC';"))
        conn.commit()
except Exception as e:
    logger.warning(f"Non-critical migration note: {e}")

# Create default law enforcement officer accounts if database is empty
db = next(get_db())
try:
    default_accounts = [
        {"username": "admin", "password": "admin123", "role": "ADMIN"},
        {"username": "investigator", "password": "password", "role": "ADMIN"},
        {"username": "analyst", "password": "password", "role": "ANALYST"},
        {"username": "forensics", "password": "password", "role": "FORENSIC_OFFICER"},
        {"username": "commander", "password": "password", "role": "COMMANDER"},
        {"username": "field_agent", "password": "password", "role": "FIELD_AGENT"}
    ]
    for acc in default_accounts:
        existing = db.query(User).filter(User.username == acc["username"]).first()
        if not existing:
            user = User(
                username=acc["username"],
                hashed_password=get_password_hash(acc["password"]),
                role=acc["role"]
            )
            db.add(user)
            logger.info(f"Created account: {acc['username']} ({acc['role']})")
    db.commit()
except Exception as e:
    logger.error(f"Error seeding default accounts: {e}")
finally:
    db.close()

app = FastAPI(
    title="AI-Powered Criminal Network Analysis System API",
    description="Investigator decision-support platform providing network intelligence, centrality analysis, and anomalies.",
    version="1.0.0"
)

# CORS configuration to connect React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(entities.router)
app.include_router(relationships.router)
app.include_router(graph.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(assistant.router)
app.include_router(reports.router)
app.include_router(investigations.router)
app.include_router(resolutions.router)
app.include_router(ml.router)
app.include_router(ml.router, prefix="/api")

@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")

@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint confirming Postgres, Neo4j status, and general API state."""
    postgres_status = "Healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        postgres_status = f"Unhealthy: {str(e)}"
        
    neo4j_status = "Connected" if is_neo4j_connected() else "Disconnected (Fallback Active)"
    
    return {
        "status": "Healthy" if postgres_status == "Healthy" else "Degraded",
        "services": {
            "postgres": postgres_status,
            "neo4j": neo4j_status
        }
    }
