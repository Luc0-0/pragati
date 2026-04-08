"""
PRAGATI - FastAPI Application
Public-facing API and web UI for the self-assembling health intelligence system.
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agents import root_orchestrator
from mcp import tool_registry
from db import alloydb_client as db

# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot the self-assembly sequence on startup."""
    print("PRAGATI starting up...")
    try:
        await root_orchestrator.boot()
        print("PRAGATI ready.")
    except Exception as e:
        print(f"Boot failed (will retry on first request): {e}")
    yield
    await db.close_pool()


app = FastAPI(
    title="PRAGATI",
    description="Self-Assembling India Health Intelligence System",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Models ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    data: list
    tools_used: list[str]
    query_metadata: dict
    total_rows: int = 0


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "booted": root_orchestrator.is_booted(),
        "tools_registered": len(tool_registry.get_all_tools()),
    }


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        result = await root_orchestrator.query(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """Shows all currently registered MCP tools -- demonstrates self-assembly."""
    tools = tool_registry.get_all_tools()
    return {
        "count": len(tools),
        "tools": [
            {
                "name": t["name"],
                "source_table": t["source_table"],
                "description": t["description"],
                "query_types": list(t["query_templates"].keys()),
            }
            for t in tools
        ],
    }


@app.get("/boot-log")
async def boot_log():
    return {"log": root_orchestrator.get_boot_log()}


@app.get("/stats")
async def stats():
    try:
        db_tools = await db.get_registered_tools()
    except Exception:
        db_tools = []
    return {
        "in_memory_tools": len(tool_registry.get_all_tools()),
        "db_registered_tools": db_tools,
    }


# ─── Web UI ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    tools = tool_registry.get_all_tools()
    boot_log = root_orchestrator.get_boot_log()
    tool_count = len(tools)
    is_booted = root_orchestrator.is_booted()

    tools_json_items = []
    for t in tools:
        tname = t["name"]
        tdesc = t["description"].replace("'", "\\'").replace('"', '\\"')
        ttable = t["source_table"]
        tkeys = list(t["query_templates"].keys())
        tools_json_items.append(
            f'{{"name":"{tname}","description":"{tdesc}","source_table":"{ttable}","query_types":{tkeys}}}'
        )
    tools_json = "[" + ",".join(tools_json_items) + "]"

    boot_log_json_items = []
    for line in boot_log:
        escaped = line.replace("\\", "\\\\").replace('"', '\\"')
        boot_log_json_items.append(f'"{escaped}"')
    boot_log_json = "[" + ",".join(boot_log_json_items) + "]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRAGATI -- India Health Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════
   PRAGATI — Clinical Precision + Cybernetic Elegance
   ═══════════════════════════════════════════════════════════════ */
:root {{
  --void: #05070e;
  --deep: #0a0f1e;
  --surface: #0d1424;
  --panel: #111a2e;
  --panel-hover: #15203a;
  --border: #1a2744;
  --border-glow: #1e3a6e;
  --cyan: #00e5ff;
  --cyan-dim: #007a8a;
  --cyan-bg: rgba(0,229,255,0.06);
  --cyan-border: rgba(0,229,255,0.15);
  --green: #00ff9d;
  --green-dim: #00805a;
  --green-bg: rgba(0,255,157,0.06);
  --green-border: rgba(0,255,157,0.15);
  --amber: #ffb800;
  --amber-dim: #8a6400;
  --amber-bg: rgba(255,184,0,0.06);
  --red: #ff3d5a;
  --text: #c8d6e5;
  --text-bright: #e8f0fe;
  --text-muted: #4a6080;
  --text-dim: #2a3f5f;
  --mono: 'DM Mono', 'Fira Code', 'SF Mono', monospace;
  --sans: 'Outfit', 'Inter', system-ui, sans-serif;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html {{ scroll-behavior: smooth; }}

body {{
  background: var(--void);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── Ambient Background ────────────────────────────────────── */
body::before {{
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 0%, rgba(0,229,255,0.04) 0%, transparent 50%),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(0,255,157,0.03) 0%, transparent 50%),
    radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,229,255,0.01) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}}

/* Grid scanline overlay */
body::after {{
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,229,255,0.008) 2px,
    rgba(0,229,255,0.008) 4px
  );
  pointer-events: none;
  z-index: 0;
}}

/* ── Header ────────────────────────────────────────────────── */
.header {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(5,7,14,0.85);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.header-left {{
  display: flex;
  align-items: center;
  gap: 16px;
}}

.logo-mark {{
  width: 36px;
  height: 36px;
  position: relative;
}}

.logo-mark svg {{
  width: 36px;
  height: 36px;
}}

.logo-type {{
  display: flex;
  flex-direction: column;
}}

.logo-type h1 {{
  font-family: var(--sans);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 3px;
  color: var(--text-bright);
  line-height: 1;
}}

.logo-type span {{
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 300;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  margin-top: 3px;
}}

.header-right {{
  display: flex;
  align-items: center;
  gap: 20px;
}}

.status-beacon {{
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
}}

.beacon-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green), 0 0 16px rgba(0,255,157,0.3);
  animation: pulse-beacon 2s ease-in-out infinite;
}}

.beacon-dot.offline {{
  background: var(--red);
  box-shadow: 0 0 8px var(--red);
  animation: none;
}}

@keyframes pulse-beacon {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.4; }}
}}

.cloud-badge {{
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--cyan);
  padding: 4px 10px;
  border: 1px solid var(--cyan-border);
  border-radius: 4px;
  background: var(--cyan-bg);
  letter-spacing: 1px;
}}

/* ── Main Layout ───────────────────────────────────────────── */
.main {{
  position: relative;
  z-index: 1;
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 32px 60px;
}}

/* ── Hero / Query Section ──────────────────────────────────── */
.hero {{
  margin-bottom: 32px;
}}

.hero-label {{
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 400;
  color: var(--cyan);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}}

.hero-label::before {{
  content: '';
  display: inline-block;
  width: 12px;
  height: 1px;
  background: var(--cyan);
}}

.query-container {{
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 4px;
  transition: border-color 0.3s, box-shadow 0.3s;
}}

.query-container:focus-within {{
  border-color: var(--cyan-border);
  box-shadow: 0 0 0 1px rgba(0,229,255,0.08), 0 8px 40px rgba(0,229,255,0.05);
}}

.query-input {{
  width: 100%;
  background: transparent;
  border: none;
  color: var(--text-bright);
  font-family: var(--sans);
  font-size: 16px;
  font-weight: 400;
  padding: 20px 24px 16px;
  resize: none;
  outline: none;
  min-height: 64px;
  max-height: 200px;
  line-height: 1.5;
}}

.query-input::placeholder {{
  color: var(--text-dim);
  font-weight: 300;
}}

.query-actions {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 8px 20px;
}}

.query-hint {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-dim);
}}

.query-hint kbd {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  font-size: 10px;
  color: var(--text-muted);
}}

.query-submit {{
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(0,229,255,0.08) 100%);
  border: 1px solid rgba(0,229,255,0.3);
  color: var(--cyan);
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 500;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}}

.query-submit:hover {{
  background: linear-gradient(135deg, rgba(0,229,255,0.25) 0%, rgba(0,229,255,0.12) 100%);
  border-color: rgba(0,229,255,0.5);
  box-shadow: 0 0 20px rgba(0,229,255,0.1);
}}

.query-submit:disabled {{
  opacity: 0.3;
  cursor: not-allowed;
}}

.query-submit svg {{
  width: 14px;
  height: 14px;
}}

/* ── Sample Questions ──────────────────────────────────────── */
.samples {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}}

.sample-pill {{
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-family: var(--sans);
  font-size: 12px;
  font-weight: 400;
  padding: 7px 14px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}}

.sample-pill:hover {{
  border-color: var(--cyan-border);
  color: var(--cyan);
  background: var(--cyan-bg);
}}

/* ── Dashboard Grid ────────────────────────────────────────── */
.dashboard {{
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
  margin-top: 24px;
}}

/* ── Cards ─────────────────────────────────────────────────── */
.card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
}}

.card-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--border);
}}

.card-title {{
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}}

.card-count {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-dim);
  padding: 2px 8px;
  background: var(--panel);
  border-radius: 4px;
}}

.card-body {{
  padding: 16px 20px 20px;
}}

/* ── Result Area ───────────────────────────────────────────── */
.result-area {{
  display: none;
}}

.result-area.visible {{
  display: block;
  animation: fadeSlideUp 0.4s ease-out;
}}

@keyframes fadeSlideUp {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.answer-block {{
  position: relative;
  padding: 20px 24px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--green-bg) 0%, rgba(0,255,157,0.02) 100%);
  border: 1px solid var(--green-border);
  margin-bottom: 16px;
}}

.answer-block::before {{
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 3px;
  background: var(--green);
  box-shadow: 0 0 10px rgba(0,255,157,0.4);
}}

.answer-text {{
  font-family: var(--sans);
  font-size: 15px;
  font-weight: 400;
  line-height: 1.75;
  color: var(--text-bright);
  padding-left: 12px;
}}

.meta-strip {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}}

.meta-tag {{
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-muted);
  padding: 5px 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
}}

.meta-tag .val {{
  color: var(--cyan);
  font-weight: 500;
}}

/* ── Data Table ────────────────────────────────────────────── */
.table-wrap {{
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}}

.table-wrap table {{
  width: 100%;
  border-collapse: collapse;
}}

.table-wrap thead th {{
  background: var(--panel);
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 2;
}}

.table-wrap tbody td {{
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 300;
  color: var(--text);
  padding: 10px 14px;
  border-bottom: 1px solid rgba(26,39,68,0.5);
  transition: background 0.15s;
}}

.table-wrap tbody tr:hover td {{
  background: rgba(0,229,255,0.03);
}}

.table-wrap tbody tr:last-child td {{
  border-bottom: none;
}}

.table-scroll {{
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}

.table-scroll::-webkit-scrollbar {{
  width: 6px;
}}

.table-scroll::-webkit-scrollbar-track {{
  background: transparent;
}}

.table-scroll::-webkit-scrollbar-thumb {{
  background: var(--border);
  border-radius: 3px;
}}

/* ── Loading State ─────────────────────────────────────────── */
.loader {{
  display: none;
  padding: 48px 24px;
  text-align: center;
}}

.loader.visible {{
  display: block;
  animation: fadeSlideUp 0.3s ease-out;
}}

.loader-bar {{
  width: 200px;
  height: 2px;
  background: var(--panel);
  border-radius: 2px;
  margin: 0 auto 16px;
  overflow: hidden;
  position: relative;
}}

.loader-bar::after {{
  content: '';
  position: absolute;
  left: -40%;
  top: 0;
  height: 100%;
  width: 40%;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
  animation: loaderSlide 1.2s ease-in-out infinite;
}}

@keyframes loaderSlide {{
  0% {{ left: -40%; }}
  100% {{ left: 100%; }}
}}

.loader-text {{
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 1px;
}}

/* ── Error State ───────────────────────────────────────────── */
.error-block {{
  display: none;
  padding: 14px 18px;
  border-radius: 10px;
  background: rgba(255,61,90,0.06);
  border: 1px solid rgba(255,61,90,0.2);
  font-family: var(--mono);
  font-size: 12px;
  color: #ff8a9e;
  margin-bottom: 16px;
}}

.error-block.visible {{
  display: block;
  animation: fadeSlideUp 0.3s ease-out;
}}

/* ── Sidebar: Tool Registry ────────────────────────────────── */
.tool-node {{
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 10px;
  background: var(--panel);
  transition: all 0.2s;
  cursor: default;
}}

.tool-node:hover {{
  border-color: var(--cyan-border);
  background: rgba(0,229,255,0.03);
}}

.tool-node-name {{
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--cyan);
  margin-bottom: 4px;
}}

.tool-node-desc {{
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 300;
  color: var(--text-muted);
  line-height: 1.5;
}}

.tool-node-tags {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 8px;
}}

.tool-tag {{
  font-family: var(--mono);
  font-size: 9px;
  color: var(--text-dim);
  padding: 2px 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 3px;
}}

/* ── Boot Log ──────────────────────────────────────────────── */
.boot-log {{
  max-height: 180px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}

.boot-line {{
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 300;
  color: var(--green);
  padding: 3px 0;
  opacity: 0;
  animation: bootFade 0.3s ease-out forwards;
  display: flex;
  align-items: baseline;
  gap: 8px;
}}

.boot-line::before {{
  content: '>';
  color: var(--green-dim);
  font-size: 10px;
  flex-shrink: 0;
}}

@keyframes bootFade {{
  from {{ opacity: 0; transform: translateX(-8px); }}
  to {{ opacity: 1; transform: translateX(0); }}
}}

/* ── Stats Row ─────────────────────────────────────────────── */
.stats-row {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}}

.stat-cell {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px;
  text-align: center;
}}

.stat-value {{
  font-family: var(--mono);
  font-size: 28px;
  font-weight: 500;
  color: var(--text-bright);
  line-height: 1;
}}

.stat-value.cyan {{ color: var(--cyan); }}
.stat-value.green {{ color: var(--green); }}
.stat-value.amber {{ color: var(--amber); }}

.stat-label {{
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 400;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 6px;
}}

/* ── Architecture Diagram ──────────────────────────────────── */
.arch-flow {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px 0;
  overflow-x: auto;
}}

.arch-node {{
  flex-shrink: 0;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 400;
  color: var(--text-muted);
  background: var(--panel);
  text-align: center;
  white-space: nowrap;
}}

.arch-node.active {{
  border-color: var(--cyan-border);
  color: var(--cyan);
  background: var(--cyan-bg);
}}

.arch-arrow {{
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-dim);
  flex-shrink: 0;
}}

/* ── Responsive ────────────────────────────────────────────── */
@media (max-width: 960px) {{
  .dashboard {{
    grid-template-columns: 1fr;
  }}
  .header {{
    padding: 0 16px;
  }}
  .main {{
    padding: 20px 16px 40px;
  }}
  .stats-row {{
    grid-template-columns: repeat(3, 1fr);
  }}
  .samples {{
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 8px;
  }}
}}

@media (max-width: 560px) {{
  .stats-row {{
    grid-template-columns: 1fr;
  }}
  .header-right .cloud-badge {{
    display: none;
  }}
}}

/* ── Utilities ─────────────────────────────────────────────── */
.sr-only {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border-width: 0;
}}
</style>
</head>
<body>

<!-- ═══ Header ═══ -->
<header class="header">
  <div class="header-left">
    <div class="logo-mark">
      <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="34" height="34" rx="8" stroke="var(--cyan)" stroke-width="1.5" fill="none" opacity="0.6"/>
        <path d="M10 18h4l3-6 3 10 3-7h4" stroke="var(--cyan)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="18" cy="18" r="2" fill="var(--cyan)" opacity="0.8"/>
      </svg>
    </div>
    <div class="logo-type">
      <h1>PRAGATI</h1>
      <span>Self-Assembling Health Intelligence</span>
    </div>
  </div>
  <div class="header-right">
    <div class="status-beacon">
      <div class="beacon-dot {"" if is_booted else "offline"}"></div>
      <span id="statusText">{"SYSTEM ONLINE" if is_booted else "BOOTING"}</span>
    </div>
    <div class="cloud-badge">GOOGLE CLOUD</div>
  </div>
</header>

<!-- ═══ Main ═══ -->
<div class="main">

  <!-- Stats Row -->
  <div class="stats-row">
    <div class="stat-cell">
      <div class="stat-value cyan" id="statTools">{tool_count}</div>
      <div class="stat-label">MCP Tools Active</div>
    </div>
    <div class="stat-cell">
      <div class="stat-value green" id="statTables">{tool_count}</div>
      <div class="stat-label">Data Sources</div>
    </div>
    <div class="stat-cell">
      <div class="stat-value amber" id="statQueries">0</div>
      <div class="stat-label">Queries Served</div>
    </div>
  </div>

  <!-- Query Section -->
  <div class="hero">
    <div class="hero-label">Query Interface</div>
    <div class="query-container">
      <textarea class="query-input" id="qInput" placeholder="Ask anything about India's public health data..." rows="2"></textarea>
      <div class="query-actions">
        <span class="query-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> to submit</span>
        <button class="query-submit" id="qBtn" onclick="submitQuery()">
          <svg viewBox="0 0 14 14" fill="none"><path d="M1 7h12M8 2l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          EXECUTE
        </button>
      </div>
    </div>
    <div class="samples" id="samplesRow"></div>
  </div>

  <!-- Dashboard -->
  <div class="dashboard">

    <!-- Left: Results Area -->
    <div>
      <div class="loader" id="loader">
        <div class="loader-bar"></div>
        <div class="loader-text">QUERYING DATABASE</div>
      </div>

      <div class="error-block" id="errorBlock"></div>

      <div class="result-area" id="resultArea">
        <div class="answer-block">
          <div class="answer-text" id="answerText"></div>
        </div>
        <div class="meta-strip" id="metaStrip"></div>
        <div class="table-wrap" id="tableWrap">
          <div class="table-scroll" id="tableScroll"></div>
        </div>
      </div>

      <!-- Architecture Flow -->
      <div class="card" style="margin-top:20px">
        <div class="card-header">
          <span class="card-title">Self-Assembly Pipeline</span>
        </div>
        <div class="card-body">
          <div class="arch-flow">
            <div class="arch-node active">AlloyDB</div>
            <div class="arch-arrow">--></div>
            <div class="arch-node active">Cartographer</div>
            <div class="arch-arrow">--></div>
            <div class="arch-node active">Forge</div>
            <div class="arch-arrow">--></div>
            <div class="arch-node active">MCP Tools</div>
            <div class="arch-arrow">--></div>
            <div class="arch-node active">Orchestrator</div>
            <div class="arch-arrow">--></div>
            <div class="arch-node active">Gemini</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Sidebar -->
    <div>
      <!-- Tool Registry -->
      <div class="card" style="margin-bottom:16px">
        <div class="card-header">
          <span class="card-title">MCP Tool Registry</span>
          <span class="card-count" id="toolCountBadge">{tool_count} tools</span>
        </div>
        <div class="card-body" id="toolsList"></div>
      </div>

      <!-- Boot Log -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Boot Sequence</span>
          <span class="card-count" id="bootStatus">{"COMPLETE" if is_booted else "PENDING"}</span>
        </div>
        <div class="card-body">
          <div class="boot-log" id="bootLog"></div>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
// ═══ Data ═══
const TOOLS_DATA = {tools_json};
const BOOT_LOG = {boot_log_json};
let queryCount = 0;

const SAMPLE_QUESTIONS = [
  "Infant mortality rate in Bihar",
  "Compare immunization across states",
  "Malaria hotspots in 2024",
  "PHC count in Rajasthan",
  "TB detection trend in Maharashtra",
  "Dengue cases in Tamil Nadu",
  "Facility summary by state",
  "Anaemia prevalence comparison",
];

// ═══ Init ═══
document.addEventListener('DOMContentLoaded', () => {{
  renderTools();
  renderBootLog();
  renderSamples();
}});

function renderTools() {{
  const el = document.getElementById('toolsList');
  if (!TOOLS_DATA.length) {{
    el.innerHTML = '<div style="font-family:var(--mono);font-size:11px;color:var(--text-dim)">Awaiting boot sequence...</div>';
    return;
  }}
  el.innerHTML = TOOLS_DATA.map(t => `
    <div class="tool-node">
      <div class="tool-node-name">${{t.name}}</div>
      <div class="tool-node-desc">${{t.description.substring(0, 100)}}${{t.description.length > 100 ? '...' : ''}}</div>
      <div class="tool-node-tags">
        ${{t.query_types.map(q => `<span class="tool-tag">${{q}}</span>`).join('')}}
      </div>
    </div>
  `).join('');
}}

function renderBootLog() {{
  const el = document.getElementById('bootLog');
  if (!BOOT_LOG.length) {{
    el.innerHTML = '<div class="boot-line" style="animation-delay:0s">Awaiting initialization...</div>';
    return;
  }}
  el.innerHTML = BOOT_LOG.map((line, i) =>
    `<div class="boot-line" style="animation-delay:${{i * 0.08}}s">${{line}}</div>`
  ).join('');
}}

function renderSamples() {{
  document.getElementById('samplesRow').innerHTML = SAMPLE_QUESTIONS.map(q =>
    `<button class="sample-pill" onclick="askQuestion('${{q}}')">${{q}}</button>`
  ).join('');
}}

function askQuestion(q) {{
  document.getElementById('qInput').value = q;
  submitQuery();
}}

async function submitQuery() {{
  const q = document.getElementById('qInput').value.trim();
  if (!q) return;

  const btn = document.getElementById('qBtn');
  btn.disabled = true;

  document.getElementById('loader').classList.add('visible');
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('errorBlock').classList.remove('visible');

  try {{
    const resp = await fetch('/query', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{question: q}})
    }});
    if (!resp.ok) {{
      const err = await resp.json();
      throw new Error(err.detail || 'Server error');
    }}
    const data = await resp.json();

    // Update query counter
    queryCount++;
    document.getElementById('statQueries').textContent = queryCount;

    // Answer
    document.getElementById('answerText').textContent = data.answer;

    // Meta
    const meta = data.query_metadata;
    document.getElementById('metaStrip').innerHTML = `
      <div class="meta-tag">TOOL <span class="val">${{data.tools_used[0] || '-'}}</span></div>
      <div class="meta-tag">PATTERN <span class="val">${{meta.query_type || '-'}}</span></div>
      ${{meta.param1 ? `<div class="meta-tag">FILTER <span class="val">${{meta.param1}}</span></div>` : ''}}
      <div class="meta-tag">ROWS <span class="val">${{data.total_rows}}</span></div>
    `;

    // Table
    const tableScroll = document.getElementById('tableScroll');
    if (data.data && data.data.length > 0) {{
      const cols = Object.keys(data.data[0]).filter(c => c !== 'embedding');
      const thead = `<thead><tr>${{cols.map(c => `<th>${{c}}</th>`).join('')}}</tr></thead>`;
      const tbody = `<tbody>${{data.data.slice(0, 20).map(row =>
        `<tr>${{cols.map(c => {{
          let v = row[c];
          if (v === null || v === undefined) v = '-';
          if (typeof v === 'number') v = Number.isInteger(v) ? v : v.toFixed(2);
          return `<td>${{v}}</td>`;
        }}).join('')}}</tr>`
      ).join('')}}</tbody>`;
      tableScroll.innerHTML = `<table>${{thead}}${{tbody}}</table>`;
    }} else {{
      tableScroll.innerHTML = '<div style="padding:24px;text-align:center;font-family:var(--mono);font-size:11px;color:var(--text-dim)">No data rows returned</div>';
    }}

    document.getElementById('resultArea').classList.add('visible');
  }} catch(e) {{
    const errEl = document.getElementById('errorBlock');
    errEl.textContent = e.message;
    errEl.classList.add('visible');
  }} finally {{
    document.getElementById('loader').classList.remove('visible');
    btn.disabled = false;
  }}
}}

// Keyboard shortcut
document.getElementById('qInput').addEventListener('keydown', e => {{
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {{
    e.preventDefault();
    submitQuery();
  }}
}});

// Auto-resize textarea
document.getElementById('qInput').addEventListener('input', function() {{
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 200) + 'px';
}});
</script>
</body>
</html>"""


# ─── Init ─────────────────────────────────────────────────────────────────────

@app.get("/api/__init__", include_in_schema=False)
async def _init():
    return {}
