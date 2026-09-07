from neo4j import GraphDatabase
import logging
from backend.app.config import settings

logger = logging.getLogger("neo4j_db")

driver = None
connected = False


def init_neo4j():
    """
    Initialize Neo4j only when explicitly enabled.

    PostgreSQL + NetworkX remain the default graph backend.
    Set NEO4J_ENABLED=true in .env when Neo4j is available.
    """
    global driver, connected

    neo4j_enabled = getattr(settings, "NEO4J_ENABLED", False)

    if not neo4j_enabled:
        driver = None
        connected = False
        return

    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=2.0
        )

        with driver.session() as session:
            session.run("RETURN 1")

        connected = True
        logger.info("Neo4j connected successfully.")

    except Exception:
        driver = None
        connected = False
        logger.info("Neo4j unavailable. Using PostgreSQL/NetworkX graph backend.")


init_neo4j()


def get_neo4j_session():
    if not connected or driver is None:
        return None

    try:
        return driver.session()
    except Exception:
        return None


def is_neo4j_connected():
    return connected