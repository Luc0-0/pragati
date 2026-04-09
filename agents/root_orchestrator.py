"""
PRAGATI - Root Orchestrator Agent
The central ADK agent that coordinates Cartographer + Forge + MCP tools
to answer natural language health data queries.
Uses Google ADK + Gemini 1.5 Flash.
"""
import os
import asyncio
import json
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content

from agents import cartographer, forge
from mcp import tool_registry

# Boot state
_booted = False
_boot_log: list[str] = []


async def boot() -> dict:
    """
    SELF-ASSEMBLY BOOT SEQUENCE:
    1. Cartographer discovers the data landscape
    2. Forge creates MCP tools from the schema
    3. Root Orchestrator is ready to serve queries
    """
    global _booted, _boot_log
    _boot_log = []

    _boot_log.append("PRAGATI booting...")
    _boot_log.append("Step 1: Cartographer mapping data landscape")
    landscape = await cartographer.discover_data_landscape()
    _boot_log.append(f"  Found {landscape['summary']['total_tables']} tables, "
                     f"{landscape['summary']['total_rows']} rows")

    _boot_log.append("Step 2: Forge creating MCP tools")
    tools = await forge.forge_tools(landscape)
    for t in tools:
        _boot_log.append(f"  Registered: {t['name']}")

    _booted = True
    _boot_log.append(f"PRAGATI ready. {len(tools)} tools active.")
    return {"landscape": landscape, "tools": tools, "boot_log": _boot_log}


def is_booted() -> bool:
    return _booted


def get_boot_log() -> list[str]:
    return _boot_log


async def query(question: str) -> dict:
    """
    Main entry point: accepts a natural language question and returns:
    - answer: Gemini-synthesized natural language response
    - data: raw rows from the database
    - tools_used: which MCP tools were invoked
    - query_metadata: what SQL patterns were used
    """
    if not _booted:
        await boot()

    tools_used = []
    query_metadata = {}

    # Step 1: Route query to best tool
    tool_name = forge.get_tool_for_query(question)
    if not tool_name:
        return {
            "answer": "No suitable data tool found for your question. Try asking about health indicators, facilities, or disease reports.",
            "data": [],
            "tools_used": [],
            "query_metadata": {},
        }

    # Step 2: Determine query type and params
    query_type, param1, param2 = forge.determine_query_type(tool_name, question)
    query_metadata = {
        "tool": tool_name,
        "query_type": query_type,
        "param1": param1,
        "param2": param2,
    }

    # Step 3: Execute the MCP tool
    try:
        data = await tool_registry.execute_tool(tool_name, query_type, param1, param2)
        tools_used.append(tool_name)
    except Exception as e:
        return {
            "answer": f"Error executing tool '{tool_name}': {str(e)}",
            "data": [],
            "tools_used": [tool_name],
            "query_metadata": query_metadata,
        }

    # Step 4: Synthesize answer with Gemini
    answer = await _synthesize_with_gemini(question, tool_name, data)

    return {
        "answer": answer,
        "data": data[:20],  # Return top 20 rows in response
        "tools_used": tools_used,
        "query_metadata": query_metadata,
        "total_rows": len(data),
    }


async def _synthesize_with_gemini(question: str, tool_used: str, data: list[dict]) -> str:
    """Use Gemini 1.5 Flash to generate a natural language answer from raw data."""
    try:
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        location = os.getenv("GCP_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        model = GenerativeModel("gemini-2.5-flash")

        # Truncate data for context window
        sample = data[:15]
        data_str = json.dumps(sample, indent=2, default=str)

        prompt = f"""You are PRAGATI, an AI health intelligence assistant for India's public health system.

A user asked: "{question}"

The system queried the '{tool_used.replace('query_', '')}' database using the '{tool_used}' MCP tool and retrieved {len(data)} records.

Here is a sample of the data (up to 15 rows):
{data_str}

Provide a clear, insightful 2-4 sentence answer to the user's question based on this data.
- Highlight key numbers, trends, or comparisons
- If the data shows concerning health indicators, note that
- Be specific about states/districts/diseases mentioned
- End with one actionable insight or recommendation
- Do NOT mention SQL, databases, or tools — speak as a health analyst"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # Fallback: return a simple summary without Gemini
        if not data:
            return "No data found for your query. Try a different state or indicator name."
        return (
            f"Found {len(data)} records using {tool_used}. "
            f"Top result: {json.dumps(data[0], default=str)}. "
            f"(Gemini synthesis unavailable: {str(e)})"
        )
