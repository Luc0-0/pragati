# PRAGATI

## Progressive Reasoning Agent for Global Advanced Total Intelligence

**India's Self-Assembling Public Health Intelligence System**

Built for Google Gen AI Academy APAC Cohort 1 Hackathon | Track 1: AI Agents with ADK

**Live Demo:** [https://pragati-366193575719.us-central1.run.app](https://pragati-366193575719.us-central1.run.app)

---

## What Makes PRAGATI Unique

Most AI agents are hand-coded with fixed tools. **PRAGATI self-assembles its own MCP tools at runtime.**

At boot, PRAGATI:

1. **Cartographer** introspects the AlloyDB schema -- no hardcoded table names
2. **Forge** dynamically generates MCP Toolbox tool definitions from the discovered schema
3. **Root Orchestrator** (ADK agent) routes natural language queries to the right tool
4. **Gemini Flash** synthesizes a natural language answer from the raw data

Add a new table to AlloyDB, restart PRAGATI, and it automatically has a new tool. Zero code changes.

---

## Architecture

```text
User Query (Natural Language)
    |
    v
Root Orchestrator (Google ADK Agent)
    |
    +---> Cartographer ---> AlloyDB introspect_tables()
    |                           |
    |                           v
    +---> Forge ----------> MCP Tool Registry (self-assembled)
                                |
                    +-----------+-----------+
                    v           v           v
              query_health  query_      query_
              _indicators   facilities  disease_reports
                    |
                    v
                AlloyDB (PostgreSQL + pgvector)
                    |
                    v
              Gemini synthesis ---> Answer + Data Table
```

---

## Stack

| Component | Technology |
| --- | --- |
| LLM | Gemini Flash (Vertex AI) |
| Agent Framework | Google ADK |
| Tool Protocol | MCP Toolbox for Databases |
| Database | AlloyDB (PostgreSQL + pgvector) |
| Embeddings | Vertex AI text-embedding-004 |
| API | FastAPI + asyncpg |
| Deployment | Cloud Run (us-central1) |

---

## Quick Start

### 1. Setup AlloyDB

```bash
bash setup_alloydb.sh YOUR_PROJECT_ID
```

### 2. Initialize Database

```bash
# Apply schema
psql -h YOUR_ALLOYDB_IP -U postgres -d pragati -f db/schema.sql

# Seed with India health data
pip install -r requirements.txt
python db/seed_data.py
```

### 3. Run Locally

```bash
cp .env.example .env
# Edit .env with your AlloyDB IP and GCP project
uvicorn api.main:app --reload --port 8080
```

### 4. Deploy to Cloud Run

```bash
bash deploy.sh YOUR_PROJECT_ID
```

---

## API Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Web UI dashboard |
| `POST /query` | Natural language health query |
| `GET /tools` | List all self-assembled MCP tools |
| `GET /boot-log` | See the self-assembly boot sequence |
| `GET /health` | Health check |
| `GET /stats` | Tool usage statistics |

---

## Sample Questions

- "What is the infant mortality rate in Bihar?"
- "Compare immunization coverage across all states"
- "Show malaria hotspots in 2024"
- "How many PHCs are there in Rajasthan?"
- "What are TB detection rate trends in Maharashtra?"
- "Dengue cases in Tamil Nadu"
- "Facility summary by state"

---

## Data

PRAGATI uses HMIS-style India public health data across:

- **10 states** x **6 districts** each
- **15 health indicators** (IMR, MMR, immunization, etc.) x 4 years
- **600+ health facilities** (PHC, CHC, hospitals)
- **Disease surveillance** for 8 diseases x 3 years
- **7,894 total rows** across 3 tables

---

## Team

**Nipun Sujesh** | Google Gen AI Academy APAC Cohort 1 | April 2026

Built with Google ADK, MCP Toolbox, AlloyDB, Vertex AI, and Cloud Run.
