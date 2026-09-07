# AI-Powered Criminal Network Analysis System

An investigator decision-support platform designed to analyze crime intelligence datasets, extract entities and relationships, build an interactive knowledge graph, calculate network metrics, and provide explainable alerts and AI assistance.

## ⚠️ Important Safety Principle
**This is a decision-support system only. The system does not determine guilt or classify individuals as criminals. All outputs are indicators and investigative leads requiring human review.**

---

## 1. Architecture Overview
The platform leverages a hybrid storage and analysis pattern to ensure robust operations even without Neo4j:
- **PostgreSQL**: Stores the structured relational data (users, documents, entities, relationships, alerts, and audit logs).
- **Neo4j**: Acts as the high-performance network query engine (Optional / Fallback active).
- **NetworkX**: In-memory graph processor used as a backend fallback when Neo4j is offline, running Louvain community detection, PageRank, betweenness centralities, and shortest paths.
- **Ollama (Llama 3.2)**: Performs NLP entity/relationship extraction and powers the AI assistant.

```text
Data Sources (CSV, TXT, PDF)
     ↓
Data Ingestion Pipeline
     ↓
NLP / Rule-Based Extractor (Ollama / Regex)
     ↓
PostgreSQL & Neo4j Sync Adapter
     ↓
Graph Analytics (NetworkX / Neo4j) ── Anomaly Models (Alerts)
     ↓
Evidence Traceability logs
     ↓
React Investigator Dashboard ── AI Assistant Chat
```

---

## 2. Technology Stack
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Cytoscape.js, Recharts, Lucide icons
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Neo4j, NetworkX
- **AI/LLM**: Ollama (`llama3.2` model), HTTP API client

---

## 3. Getting Started (Running Locally)

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL running locally (default: port 5432)
- Ollama running locally (default: port 11434) with `llama3.2` downloaded (`ollama pull llama3.2`)

### 1. Database Setup
Create a PostgreSQL database named `postgres` (or modify `DATABASE_URL` in `.env`):
```sql
CREATE DATABASE postgres;
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and adjust database credentials:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
NEO4J_URI=bolt://localhost:7687
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 3. Backend Setup & Seeding
Install dependencies and run the seed script:
```bash
# From workspace root
pip install -r backend/requirements.txt
python scripts/seed_database.py
```
*Note: Seeding generates a complete crime network containing 55 persons, 32 phones, 22 vehicles, and 47 active anomalies (cycles, overlaps, spikes).*

### 4. Running the Servers
Start the FastAPI server:
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the React dev server:
```bash
# In a new terminal (from workspace root)
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` (or the port specified by Vite) and log in with:
- **Username**: `investigator`
- **Password**: `password`

---

## 4. API Endpoints
- `POST /api/auth/login`: Authenticate and obtain JWT token.
- `POST /api/upload`: Ingest unstructured reports or structured CSV tables.
- `GET /api/entities`: Search nodes by ID, name, or type.
- `GET /api/entities/{id}/connections`: Progressive 1-hop neighbor expansion.
- `GET /api/graph`: Complete graph representation (nodes & edges).
- `GET /api/graph/shortest-path`: Find the connectivity path between two nodes.
- `GET /api/analytics/centrality`: Fetch PageRank and other centrality scores.
- `GET /api/analytics/communities`: Louvain community detection assignments.
- `GET /api/alerts`: List behavioral anomalies and warning alerts.
- `POST /api/assistant`: Ask AI questions about the network context.
- `POST /api/reports`: Generate compiled investigation summary report.

---

## 5. Security & Privacy
- **JWT Authentication**: Secured endpoints utilizing token-based validation.
- **Role-Based Access Control (RBAC)**: Supports roles: `ADMIN`, `INVESTIGATOR`, `ANALYST`, `VIEWER`.
- **Audit Logs**: All queries, uploads, logins, and report generations are permanently recorded in the database audit log.
