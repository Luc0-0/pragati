"""
PRAGATI - MCP Tool Registry
The self-assembly engine: dynamically creates and manages MCP Toolbox tool definitions
at runtime based on discovered database schema.
"""
import asyncio
from typing import Any
from db import alloydb_client as db

# In-memory registry (source of truth for active session)
_tools: dict[str, dict] = {}

# Descriptions auto-generated per table
_TABLE_DESCRIPTIONS = {
    "health_indicators": (
        "Query India health indicators (IMR, MMR, immunization coverage, etc.) "
        "by state, district, year, or indicator name."
    ),
    "facilities": (
        "Query health facility data (PHCs, CHCs, hospitals) by state/district, "
        "including bed count and staff numbers."
    ),
    "disease_reports": (
        "Query disease surveillance data (malaria, dengue, TB, etc.) "
        "by state, district, disease, year, or month."
    ),
}

# SQL templates per table for common query patterns
_QUERY_TEMPLATES = {
    "health_indicators": {
        "by_state": "SELECT state, district, year, indicator_name, value, unit FROM health_indicators WHERE state ILIKE $1 ORDER BY year DESC, indicator_name LIMIT 50",
        "by_indicator": "SELECT state, district, year, value, unit FROM health_indicators WHERE indicator_name ILIKE $1 ORDER BY year DESC, state LIMIT 50",
        "compare_states": "SELECT state, AVG(value) as avg_value, indicator_name FROM health_indicators WHERE indicator_name ILIKE $1 GROUP BY state, indicator_name ORDER BY avg_value",
        "trend": "SELECT year, AVG(value) as avg_value FROM health_indicators WHERE state ILIKE $1 AND indicator_name ILIKE $2 GROUP BY year ORDER BY year",
        "all": "SELECT state, district, year, indicator_name, value, unit, category FROM health_indicators ORDER BY year DESC, state LIMIT 100",
    },
    "facilities": {
        "by_state": "SELECT name, state, district, facility_type, beds, staff_count, is_functional FROM facilities WHERE state ILIKE $1 ORDER BY facility_type, name LIMIT 50",
        "by_type": "SELECT name, state, district, beds, staff_count FROM facilities WHERE facility_type ILIKE $1 ORDER BY beds DESC LIMIT 50",
        "summary": "SELECT state, facility_type, COUNT(*) as count, SUM(beds) as total_beds FROM facilities GROUP BY state, facility_type ORDER BY state, facility_type",
        "all": "SELECT name, state, district, facility_type, beds, staff_count, is_functional FROM facilities LIMIT 100",
    },
    "disease_reports": {
        "by_state": "SELECT state, district, disease, SUM(cases) as total_cases, SUM(deaths) as total_deaths, year FROM disease_reports WHERE state ILIKE $1 GROUP BY state, district, disease, year ORDER BY total_cases DESC LIMIT 50",
        "by_disease": "SELECT state, district, year, month, cases, deaths FROM disease_reports WHERE disease ILIKE $1 ORDER BY year DESC, cases DESC LIMIT 50",
        "hotspots": "SELECT state, district, disease, SUM(cases) as total_cases FROM disease_reports WHERE year = $1 GROUP BY state, district, disease ORDER BY total_cases DESC LIMIT 20",
        "trend": "SELECT year, month, SUM(cases) as total_cases FROM disease_reports WHERE disease ILIKE $1 AND state ILIKE $2 GROUP BY year, month ORDER BY year, month",
        "all": "SELECT state, district, disease, cases, deaths, year, month FROM disease_reports ORDER BY year DESC, cases DESC LIMIT 100",
    },
}


def _build_tool_definition(table_name: str, columns: list[dict]) -> dict:
    """
    SELF-ASSEMBLY: Construct a full MCP tool definition from a table's schema.
    This is what makes PRAGATI unique — tools are generated from DB introspection.
    """
    col_names = [c["column_name"] for c in columns]
    description = _TABLE_DESCRIPTIONS.get(
        table_name,
        f"Query the {table_name} table. Available columns: {', '.join(col_names)}"
    )
    templates = _QUERY_TEMPLATES.get(table_name, {
        "all": f"SELECT * FROM {table_name} LIMIT 100"
    })

    return {
        "name": f"query_{table_name}",
        "source_table": table_name,
        "description": description,
        "columns": columns,
        "query_templates": templates,
        "parameters": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "description": f"Query pattern to use. Options: {list(templates.keys())}",
                    "enum": list(templates.keys()),
                },
                "param1": {
                    "type": "string",
                    "description": "Primary filter value (state name, indicator name, disease name, etc.)",
                },
                "param2": {
                    "type": "string",
                    "description": "Secondary filter value if needed (e.g., indicator name for trend query)",
                },
            },
            "required": ["query_type"],
        },
    }


async def register_tool(table_name: str, columns: list[dict]) -> dict:
    """
    Register a new MCP tool for a discovered table.
    Stores in memory AND persists to AlloyDB registry table.
    """
    tool_def = _build_tool_definition(table_name, columns)
    _tools[tool_def["name"]] = tool_def

    # Persist to AlloyDB for auditability
    try:
        await db.register_tool_in_db(
            tool_name=tool_def["name"],
            source_table=table_name,
            description=tool_def["description"],
            columns=columns,
        )
    except Exception as e:
        print(f"Warning: Could not persist tool to DB: {e}")

    return tool_def


async def bootstrap_tools() -> list[dict]:
    """
    SELF-ASSEMBLY BOOT SEQUENCE:
    1. Introspect AlloyDB schema
    2. Generate tool definitions for each table
    3. Register all tools
    Returns list of registered tools.
    """
    print("PRAGATI: Starting self-assembly boot sequence...")
    tables = await db.introspect_tables()
    registered = []
    for table in tables:
        tool = await register_tool(table["table_name"], table["columns"])
        registered.append(tool)
        print(f"  Registered tool: {tool['name']} ({len(table['columns'])} columns)")
    print(f"Self-assembly complete. {len(registered)} tools registered.")
    return registered


def get_all_tools() -> list[dict]:
    return list(_tools.values())


def get_tool(name: str) -> dict | None:
    return _tools.get(name)


async def execute_tool(tool_name: str, query_type: str, param1: str = None, param2: str = None) -> list[dict]:
    """Execute a registered MCP tool query."""
    tool = get_tool(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not registered")

    templates = tool["query_templates"]
    if query_type not in templates:
        raise ValueError(f"Unknown query_type '{query_type}' for tool '{tool_name}'")

    sql = templates[query_type]

    # Build params list based on how many $N placeholders exist
    params = []
    if "$1" in sql and param1:
        params.append(f"%{param1}%")
    if "$2" in sql and param2:
        params.append(f"%{param2}%")

    result = await db.execute_query(sql, params if params else None)
    await db.increment_tool_call_count(tool_name)
    return result
