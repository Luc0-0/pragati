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
    """Shows all currently registered MCP tools — demonstrates self-assembly."""
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
    tools_html = "".join(
        f'<div class="tool-badge">{t["name"]}</div>' for t in tools
    )
    boot_log = root_orchestrator.get_boot_log()
    boot_log_html = "".join(f"<div class='log-line'>{line}</div>" for line in boot_log)

    sample_qs = [
        "What is the infant mortality rate in Bihar?",
        "Compare immunization coverage across all states",
        "Show malaria hotspots in 2024",
        "How many PHCs are there in Rajasthan?",
        "What are the TB detection rates trend in Maharashtra?",
        "Show dengue cases in Tamil Nadu",
    ]
    sample_btns = "".join(
        f'<button class="sample-btn" onclick="askQuestion(\'{q}\')">{q}</button>'
        for q in sample_qs
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRAGATI — India Health Intelligence</title>
<style>
  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --card: #1a2235;
    --border: #2a3a55;
    --accent: #3b82f6;
    --accent2: #10b981;
    --accent3: #f59e0b;
    --text: #e2e8f0;
    --muted: #64748b;
    --danger: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }}

  header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .logo {{ display: flex; align-items: center; gap: 12px; }}
  .logo-icon {{ width: 44px; height: 44px; background: var(--accent); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }}
  .logo-text h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
  .logo-text p {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .badge {{ background: var(--accent2); color: #000; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }}

  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px; }}

  .grid {{ display: grid; grid-template-columns: 340px 1fr; gap: 24px; }}

  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
  }}
  .card h3 {{ font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 14px; }}

  .tool-badge {{
    display: inline-block;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: var(--accent);
    font-size: 12px; font-family: monospace;
    padding: 4px 10px; border-radius: 6px; margin: 3px;
  }}

  .log-line {{ font-family: monospace; font-size: 12px; color: var(--accent2); margin: 2px 0; }}

  .query-box {{ margin-bottom: 24px; }}
  .query-box textarea {{
    width: 100%; background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; color: var(--text); font-size: 15px;
    padding: 14px 16px; resize: vertical; min-height: 80px;
    outline: none; transition: border-color 0.2s;
  }}
  .query-box textarea:focus {{ border-color: var(--accent); }}
  .query-box button {{
    margin-top: 10px; width: 100%;
    background: var(--accent); color: #fff; border: none;
    border-radius: 10px; padding: 13px; font-size: 15px; font-weight: 600;
    cursor: pointer; transition: background 0.2s;
  }}
  .query-box button:hover {{ background: #2563eb; }}
  .query-box button:disabled {{ background: var(--muted); cursor: not-allowed; }}

  .sample-btn {{
    display: block; width: 100%;
    background: var(--surface); border: 1px solid var(--border);
    color: var(--text); text-align: left; font-size: 13px;
    padding: 9px 12px; border-radius: 8px; cursor: pointer;
    margin-bottom: 6px; transition: border-color 0.2s;
  }}
  .sample-btn:hover {{ border-color: var(--accent); color: var(--accent); }}

  .result-card {{ display: none; }}
  .result-card.visible {{ display: block; }}

  .answer-box {{
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 10px; padding: 16px; margin-bottom: 16px;
    font-size: 15px; line-height: 1.7; color: #d1fae5;
  }}

  .meta-row {{
    display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px;
  }}
  .meta-chip {{
    background: var(--surface); border: 1px solid var(--border);
    font-size: 12px; padding: 4px 10px; border-radius: 20px; color: var(--muted);
  }}
  .meta-chip span {{ color: var(--text); font-weight: 600; }}

  .data-table-wrap {{ overflow-x: auto; border-radius: 10px; border: 1px solid var(--border); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: var(--surface); color: var(--muted); padding: 10px 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
  td {{ padding: 9px 12px; border-top: 1px solid var(--border); color: var(--text); }}
  tr:hover td {{ background: rgba(255,255,255,0.02); }}

  .spinner {{ display: none; text-align: center; padding: 40px; color: var(--muted); font-size: 14px; }}
  .spinner.visible {{ display: block; }}

  .error-box {{
    display: none;
    background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px; padding: 14px; color: #fca5a5; font-size: 14px;
  }}
  .error-box.visible {{ display: block; }}

  @media (max-width: 768px) {{
    .grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">🏥</div>
    <div class="logo-text">
      <h1>PRAGATI</h1>
      <p>Progressive Reasoning Agent for Global Advanced Total Intelligence</p>
    </div>
  </div>
  <div class="badge">LIVE · Google Cloud</div>
</header>

<div class="container">
  <div class="grid">

    <!-- Left Panel -->
    <div>
      <div class="card" style="margin-bottom:20px">
        <h3>Self-Assembled MCP Tools</h3>
        <div>{tools_html if tools_html else '<span style="color:var(--muted);font-size:13px">Booting...</span>'}</div>
      </div>

      <div class="card" style="margin-bottom:20px">
        <h3>Boot Log</h3>
        <div style="max-height:160px;overflow-y:auto">
          {boot_log_html if boot_log_html else '<span class="log-line">Waiting for boot...</span>'}
        </div>
      </div>

      <div class="card">
        <h3>Sample Questions</h3>
        {sample_btns}
      </div>
    </div>

    <!-- Right Panel -->
    <div>
      <div class="query-box">
        <textarea id="questionInput" placeholder="Ask anything about India's public health data...&#10;e.g. What is the infant mortality rate in Bihar?"></textarea>
        <button id="askBtn" onclick="submitQuery()">Ask PRAGATI</button>
      </div>

      <div class="spinner" id="spinner">Thinking... PRAGATI is querying the database</div>
      <div class="error-box" id="errorBox"></div>

      <div class="result-card card" id="resultCard">
        <div class="answer-box" id="answerBox"></div>
        <div class="meta-row" id="metaRow"></div>
        <div class="data-table-wrap" id="tableWrap"></div>
      </div>
    </div>

  </div>
</div>

<script>
function askQuestion(q) {{
  document.getElementById('questionInput').value = q;
  submitQuery();
}}

async function submitQuery() {{
  const question = document.getElementById('questionInput').value.trim();
  if (!question) return;

  document.getElementById('askBtn').disabled = true;
  document.getElementById('spinner').classList.add('visible');
  document.getElementById('resultCard').classList.remove('visible');
  document.getElementById('errorBox').classList.remove('visible');

  try {{
    const resp = await fetch('/query', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{question}})
    }});
    if (!resp.ok) throw new Error((await resp.json()).detail || 'Server error');
    const data = await resp.json();

    document.getElementById('answerBox').textContent = data.answer;

    const meta = data.query_metadata;
    document.getElementById('metaRow').innerHTML = `
      <div class="meta-chip">Tool: <span>${{data.tools_used[0] || '—'}}</span></div>
      <div class="meta-chip">Query: <span>${{meta.query_type || '—'}}</span></div>
      ${{meta.param1 ? `<div class="meta-chip">Filter: <span>${{meta.param1}}</span></div>` : ''}}
      <div class="meta-chip">Rows: <span>${{data.total_rows}}</span></div>
    `;

    if (data.data && data.data.length > 0) {{
      const cols = Object.keys(data.data[0]);
      const thead = `<thead><tr>${{cols.map(c=>`<th>${{c}}</th>`).join('')}}</tr></thead>`;
      const tbody = `<tbody>${{data.data.map(row =>
        `<tr>${{cols.map(c=>`<td>${{row[c] ?? ''}}</td>`).join('')}}</tr>`
      ).join('')}}</tbody>`;
      document.getElementById('tableWrap').innerHTML = `<table>${{thead}}${{tbody}}</table>`;
    }} else {{
      document.getElementById('tableWrap').innerHTML = '<p style="padding:16px;color:var(--muted);font-size:13px">No data rows returned.</p>';
    }}

    document.getElementById('resultCard').classList.add('visible');
  }} catch(e) {{
    document.getElementById('errorBox').textContent = 'Error: ' + e.message;
    document.getElementById('errorBox').classList.add('visible');
  }} finally {{
    document.getElementById('spinner').classList.remove('visible');
    document.getElementById('askBtn').disabled = false;
  }}
}}

document.getElementById('questionInput').addEventListener('keydown', e => {{
  if (e.ctrlKey && e.key === 'Enter') submitQuery();
}});
</script>
</body>
</html>"""


# ─── Init ─────────────────────────────────────────────────────────────────────

@app.get("/api/__init__", include_in_schema=False)
async def _init():
    return {}
