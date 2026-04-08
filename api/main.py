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
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Sora:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #09090b;
  --surface: #0f0f12;
  --elevated: #141418;
  --card: #18181c;
  --border: rgba(255,255,255,0.06);
  --border-subtle: rgba(255,255,255,0.04);
  --border-active: rgba(255,255,255,0.12);
  --accent: #c8a97e;
  --accent-soft: rgba(200,169,126,0.12);
  --accent-border: rgba(200,169,126,0.2);
  --accent-dim: #8a7456;
  --success: #5cc98a;
  --success-soft: rgba(92,201,138,0.1);
  --success-border: rgba(92,201,138,0.2);
  --error: #e85d6f;
  --text: #a1a1aa;
  --text-primary: #fafafa;
  --text-secondary: #71717a;
  --text-tertiary: #3f3f46;
  --mono: 'JetBrains Mono', 'SF Mono', monospace;
  --sans: 'Sora', system-ui, sans-serif;
  --radius: 12px;
  --radius-sm: 8px;
  --radius-xs: 6px;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* Subtle warm gradient ambient */
body::before {{
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 50% at 30% -10%, rgba(200,169,126,0.03) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 70% 110%, rgba(200,169,126,0.02) 0%, transparent 50%);
  pointer-events: none;
}}

/* ── Nav ── */
nav {{
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  background: rgba(9,9,11,0.8);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}}

.nav-left {{
  display: flex;
  align-items: center;
  gap: 14px;
}}

.nav-logo {{
  display: flex;
  align-items: center;
  gap: 10px;
}}

.logo-symbol {{
  width: 28px;
  height: 28px;
  border: 1.5px solid var(--accent);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}}

.logo-symbol::after {{
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--accent);
  opacity: 0.7;
}}

.logo-name {{
  font-family: var(--sans);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 2px;
}}

.nav-sep {{
  width: 1px;
  height: 20px;
  background: var(--border);
}}

.nav-sub {{
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 400;
}}

.nav-right {{
  display: flex;
  align-items: center;
  gap: 14px;
}}

.nav-status {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-secondary);
}}

.dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  animation: breathe 3s ease-in-out infinite;
}}

.dot.off {{ background: var(--error); animation: none; }}

@keyframes breathe {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.35; }}
}}

.nav-tag {{
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 1px;
  color: var(--accent-dim);
  padding: 3px 8px;
  border: 1px solid var(--accent-border);
  border-radius: 4px;
}}

/* ── Layout ── */
.wrap {{
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 28px 60px;
}}

/* ── Top Row ── */
.top-row {{
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-bottom: 20px;
}}

.metrics {{
  display: flex;
  gap: 1px;
  background: var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  flex-shrink: 0;
}}

.metric {{
  background: var(--surface);
  padding: 14px 22px;
  text-align: center;
  min-width: 100px;
}}

.metric:first-child {{ border-radius: var(--radius) 0 0 var(--radius); }}
.metric:last-child {{ border-radius: 0 var(--radius) var(--radius) 0; }}

.metric-val {{
  font-family: var(--mono);
  font-size: 24px;
  font-weight: 300;
  color: var(--text-primary);
  letter-spacing: -1px;
}}

.metric-label {{
  font-family: var(--mono);
  font-size: 8px;
  font-weight: 400;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-top: 4px;
}}

.pipeline-inline {{
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}}

.pipe-label {{
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
}}

/* ── Main Layout 2-col ── */
.layout {{
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}}

.col-main {{ min-width: 0; }}
.col-side {{ min-width: 0; }}

/* ── Query ── */

.query-box {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: border-color 0.3s;
}}

.query-box:focus-within {{
  border-color: var(--border-active);
}}

.query-box textarea {{
  width: 100%;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: var(--sans);
  font-size: 15px;
  font-weight: 400;
  padding: 18px 22px 12px;
  resize: none;
  outline: none;
  min-height: 56px;
  max-height: 180px;
  line-height: 1.5;
}}

.query-box textarea::placeholder {{ color: var(--text-tertiary); }}

.query-bar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 6px 18px;
  border-top: 1px solid var(--border-subtle);
}}

.query-bar-hint {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-tertiary);
}}

.query-bar-hint kbd {{
  display: inline-block;
  background: var(--elevated);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 4px;
  font-family: var(--mono);
  font-size: 9px;
  color: var(--text-secondary);
}}

.btn-submit {{
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--accent);
  border: none;
  color: var(--bg);
  font-family: var(--sans);
  font-size: 12px;
  font-weight: 600;
  padding: 9px 18px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  letter-spacing: 0.5px;
}}

.btn-submit:hover {{ opacity: 0.9; }}
.btn-submit:active {{ transform: scale(0.97); }}
.btn-submit:disabled {{ opacity: 0.3; cursor: not-allowed; }}

.btn-submit svg {{ width: 12px; height: 12px; }}

/* ── Suggestions ── */
.suggestions {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 10px 0 16px;
}}

.suggestion {{
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-family: var(--sans);
  font-size: 11.5px;
  font-weight: 400;
  padding: 6px 14px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.15s;
}}

.suggestion:hover {{
  border-color: var(--accent-border);
  color: var(--accent);
}}

/* ── Panels ── */
.panel {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}}

.panel-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
}}

.panel-title {{
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: 1px;
  text-transform: uppercase;
}}

.panel-badge {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-tertiary);
}}

.panel-body {{ padding: 16px 18px; }}

/* ── Loader ── */
.loader {{ display: none; padding: 52px 20px; text-align: center; }}
.loader.on {{ display: block; animation: fadeIn 0.2s ease; }}

.loader-track {{
  width: 140px;
  height: 1.5px;
  background: var(--elevated);
  border-radius: 1px;
  margin: 0 auto 14px;
  overflow: hidden;
}}

.loader-track::after {{
  content: '';
  display: block;
  width: 40%;
  height: 100%;
  background: var(--accent);
  animation: slide 1s ease-in-out infinite;
}}

@keyframes slide {{
  0% {{ transform: translateX(-100%); }}
  100% {{ transform: translateX(350%); }}
}}

@keyframes fadeIn {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}

.loader-label {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 1px;
}}

/* ── Error ── */
.err {{ display: none; margin-bottom: 16px; }}
.err.on {{
  display: block;
  padding: 12px 16px;
  background: rgba(232,93,111,0.06);
  border: 1px solid rgba(232,93,111,0.15);
  border-radius: var(--radius-sm);
  font-family: var(--mono);
  font-size: 12px;
  color: var(--error);
}}

/* ── Result ── */
.result {{ display: none; }}
.result.on {{ display: block; animation: resultIn 0.35s ease-out; }}

@keyframes resultIn {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.answer {{
  padding: 20px;
  border-radius: var(--radius-sm);
  background: var(--elevated);
  border-left: 3px solid var(--accent);
  margin-bottom: 16px;
}}

.answer p {{
  font-family: var(--sans);
  font-size: 14.5px;
  font-weight: 400;
  line-height: 1.8;
  color: var(--text-primary);
}}

.tags {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}}

.tag {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-secondary);
  padding: 4px 10px;
  background: var(--elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  display: flex;
  align-items: center;
  gap: 4px;
}}

.tag b {{ color: var(--text-primary); font-weight: 500; }}

/* ── Table ── */
.tbl-wrap {{
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}}

.tbl-scroll {{
  max-height: 380px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}

.tbl-scroll::-webkit-scrollbar {{ width: 4px; }}
.tbl-scroll::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

.tbl-scroll table {{
  width: 100%;
  border-collapse: collapse;
}}

.tbl-scroll th {{
  background: var(--card);
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 10px 12px;
  text-align: left;
  position: sticky;
  top: 0;
  z-index: 2;
}}

.tbl-scroll td {{
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 300;
  color: var(--text);
  padding: 9px 12px;
  border-top: 1px solid var(--border-subtle);
}}

.tbl-scroll tr:hover td {{ background: rgba(200,169,126,0.02); }}

/* ── Pipeline ── */
.pipeline {{
  display: flex;
  align-items: center;
  gap: 0;
  padding: 4px 0;
  overflow-x: auto;
}}

.pipe-node {{
  padding: 7px 12px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--elevated);
  border: 1px solid var(--border);
  white-space: nowrap;
}}

.pipe-node:first-child {{ border-radius: var(--radius-xs) 0 0 var(--radius-xs); }}
.pipe-node:last-child {{ border-radius: 0 var(--radius-xs) var(--radius-xs) 0; }}

.pipe-node.lit {{
  color: var(--accent);
  border-color: var(--accent-border);
  background: var(--accent-soft);
}}

/* ── Tool Cards ── */
.tool {{
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  transition: border-color 0.15s;
}}

.tool:hover {{ border-color: var(--border-active); }}

.tool-name {{
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}}

.tool-desc {{
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 300;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}}

.tool-chips {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}}

.chip {{
  font-family: var(--mono);
  font-size: 9px;
  color: var(--text-tertiary);
  padding: 2px 6px;
  border: 1px solid var(--border);
  border-radius: 3px;
}}

/* ── Boot Log ── */
.log-scroll {{
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}

.log-line {{
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 300;
  color: var(--success);
  padding: 2px 0;
  opacity: 0;
  animation: logIn 0.25s ease forwards;
}}

.log-line::before {{
  content: '~ ';
  color: var(--text-tertiary);
}}

@keyframes logIn {{
  from {{ opacity: 0; transform: translateX(-4px); }}
  to {{ opacity: 1; transform: translateX(0); }}
}}

/* ── Footer ── */
.foot {{
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
  text-align: center;
}}

.foot p {{
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 0.5px;
}}

.foot p span {{ color: var(--accent-dim); }}

/* ── Boot Log compact ── */
.log-scroll {{ max-height: 150px; }}

/* ── Responsive ── */
@media (max-width: 960px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .top-row {{ flex-direction: column; }}
  nav {{ padding: 0 16px; }}
  .wrap {{ padding: 16px 16px 40px; }}
  .suggestions {{ flex-wrap: nowrap; overflow-x: auto; padding-bottom: 4px; }}
}}
</style>
</head>
<body>

<nav>
  <div class="nav-left">
    <div class="nav-logo">
      <div class="logo-symbol"></div>
      <span class="logo-name">PRAGATI</span>
    </div>
    <div class="nav-sep"></div>
    <span class="nav-sub">Health Intelligence</span>
  </div>
  <div class="nav-right">
    <div class="nav-status">
      <div class="dot {"" if is_booted else "off"}"></div>
      <span>{"Online" if is_booted else "Booting"}</span>
    </div>
    <div class="nav-tag">Google Cloud</div>
  </div>
</nav>

<div class="wrap">

  <!-- Top bar: metrics + pipeline inline -->
  <div class="top-row">
    <div class="metrics">
      <div class="metric">
        <div class="metric-val" id="mTools">{tool_count}</div>
        <div class="metric-label">Tools</div>
      </div>
      <div class="metric">
        <div class="metric-val" id="mSources">{tool_count}</div>
        <div class="metric-label">Sources</div>
      </div>
      <div class="metric">
        <div class="metric-val" id="mQueries">0</div>
        <div class="metric-label">Queries</div>
      </div>
    </div>
    <div class="pipeline-inline">
      <span class="pipe-label">Pipeline</span>
      <div class="pipeline">
        <div class="pipe-node lit">AlloyDB</div>
        <div class="pipe-node lit">Cartographer</div>
        <div class="pipe-node lit">Forge</div>
        <div class="pipe-node lit">MCP Registry</div>
        <div class="pipe-node lit">Orchestrator</div>
        <div class="pipe-node lit">Gemini</div>
      </div>
    </div>
  </div>

  <!-- Main 2-col: left=query+results, right=tools+boot -->
  <div class="layout">
    <!-- Left column -->
    <div class="col-main">
      <div class="query-box">
        <textarea id="qIn" placeholder="Ask about India's public health data..." rows="2"></textarea>
        <div class="query-bar">
          <span class="query-bar-hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></span>
          <button class="btn-submit" id="qBtn" onclick="go()">
            <svg viewBox="0 0 12 12" fill="none"><path d="M1 6h10M7 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Query
          </button>
        </div>
      </div>
      <div class="suggestions" id="suggs"></div>

      <div class="loader" id="loader">
        <div class="loader-track"></div>
        <div class="loader-label">Processing</div>
      </div>
      <div class="err" id="err"></div>

      <div class="result" id="result">
        <div class="answer"><p id="ansText"></p></div>
        <div class="tags" id="tagRow"></div>
        <div class="tbl-wrap"><div class="tbl-scroll" id="tblScroll"></div></div>
      </div>
    </div>

    <!-- Right column -->
    <div class="col-side">
      <div class="panel">
        <div class="panel-head">
          <span class="panel-title">Tool Registry</span>
          <span class="panel-badge">{tool_count} active</span>
        </div>
        <div class="panel-body" id="toolList"></div>
      </div>

      <div class="panel" style="margin-top:10px">
        <div class="panel-head">
          <span class="panel-title">Boot Sequence</span>
          <span class="panel-badge">{"Done" if is_booted else "..."}</span>
        </div>
        <div class="panel-body">
          <div class="log-scroll" id="bootLog"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="foot">
    <p>PRAGATI <span>/</span> ADK + MCP Toolbox + AlloyDB + Gemini <span>/</span> Google Gen AI Academy APAC 2026</p>
  </div>

</div>

<script>
const TOOLS = {tools_json};
const LOG = {boot_log_json};
let qc = 0;

const SUGGS = [
  "Infant mortality in Bihar",
  "Immunization coverage comparison",
  "Malaria hotspots 2024",
  "PHCs in Rajasthan",
  "TB trend in Maharashtra",
  "Dengue in Tamil Nadu",
  "Facility summary",
  "Anaemia prevalence",
];

document.addEventListener('DOMContentLoaded', () => {{
  renderTools();
  renderLog();
  renderSuggs();
}});

function renderTools() {{
  const el = document.getElementById('toolList');
  if (!TOOLS.length) {{ el.innerHTML = '<div style="font-family:var(--mono);font-size:11px;color:var(--text-tertiary)">Awaiting boot...</div>'; return; }}
  el.innerHTML = TOOLS.map(t => `
    <div class="tool">
      <div class="tool-name">${{t.name}}</div>
      <div class="tool-desc">${{t.description.length > 90 ? t.description.substring(0,90)+'...' : t.description}}</div>
      <div class="tool-chips">${{t.query_types.map(q=>`<span class="chip">${{q}}</span>`).join('')}}</div>
    </div>
  `).join('');
}}

function renderLog() {{
  const el = document.getElementById('bootLog');
  if (!LOG.length) {{ el.innerHTML = '<div class="log-line" style="animation-delay:0s">Waiting...</div>'; return; }}
  el.innerHTML = LOG.map((l,i) => `<div class="log-line" style="animation-delay:${{i*0.06}}s">${{l}}</div>`).join('');
}}

function renderSuggs() {{
  document.getElementById('suggs').innerHTML = SUGGS.map(s =>
    `<button class="suggestion" onclick="ask('${{s}}')">${{s}}</button>`
  ).join('');
}}

function ask(q) {{ document.getElementById('qIn').value = q; go(); }}

async function go() {{
  const q = document.getElementById('qIn').value.trim();
  if (!q) return;
  const btn = document.getElementById('qBtn');
  btn.disabled = true;
  document.getElementById('loader').classList.add('on');
  document.getElementById('result').classList.remove('on');
  document.getElementById('err').classList.remove('on');

  try {{
    const r = await fetch('/query', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{question:q}})
    }});
    if (!r.ok) {{ const e = await r.json(); throw new Error(e.detail||'Error'); }}
    const d = await r.json();
    qc++;
    document.getElementById('mQueries').textContent = qc;
    document.getElementById('ansText').textContent = d.answer;

    const m = d.query_metadata;
    document.getElementById('tagRow').innerHTML = `
      <div class="tag">tool <b>${{d.tools_used[0]||'-'}}</b></div>
      <div class="tag">pattern <b>${{m.query_type||'-'}}</b></div>
      ${{m.param1 ? `<div class="tag">filter <b>${{m.param1}}</b></div>` : ''}}
      <div class="tag">rows <b>${{d.total_rows}}</b></div>
    `;

    const ts = document.getElementById('tblScroll');
    if (d.data && d.data.length) {{
      const cols = Object.keys(d.data[0]).filter(c=>c!=='embedding');
      ts.innerHTML = `<table>
        <thead><tr>${{cols.map(c=>`<th>${{c}}</th>`).join('')}}</tr></thead>
        <tbody>${{d.data.slice(0,20).map(row=>`<tr>${{cols.map(c=>{{
          let v=row[c]; if(v==null)v='-'; if(typeof v==='number')v=Number.isInteger(v)?v:v.toFixed(2);
          return `<td>${{v}}</td>`;
        }}).join('')}}</tr>`).join('')}}</tbody></table>`;
    }} else {{
      ts.innerHTML = '<div style="padding:20px;text-align:center;font-family:var(--mono);font-size:11px;color:var(--text-tertiary)">No rows</div>';
    }}
    document.getElementById('result').classList.add('on');
  }} catch(e) {{
    const el = document.getElementById('err');
    el.textContent = e.message;
    el.classList.add('on');
  }} finally {{
    document.getElementById('loader').classList.remove('on');
    btn.disabled = false;
  }}
}}

document.getElementById('qIn').addEventListener('keydown', e => {{
  if ((e.ctrlKey||e.metaKey) && e.key==='Enter') {{ e.preventDefault(); go(); }}
}});

document.getElementById('qIn').addEventListener('input', function() {{
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 180) + 'px';
}});
</script>
</body>
</html>"""


# ─── Init ─────────────────────────────────────────────────────────────────────

@app.get("/api/__init__", include_in_schema=False)
async def _init():
    return {}
