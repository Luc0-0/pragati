"""
PRAGATI - AlloyDB Client
Async database client with schema introspection and Vertex AI embeddings
"""
import os
import asyncpg
import json
from typing import Any
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
import vertexai

_pool: asyncpg.Pool | None = None
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        project = os.getenv("GCP_PROJECT")
        location = os.getenv("GCP_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)
        _embed_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    return _embed_model


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = (
            f"postgresql://{os.getenv('ALLOYDB_USER', 'postgres')}:"
            f"{os.getenv('ALLOYDB_PASS', 'postgres')}@"
            f"{os.getenv('ALLOYDB_HOST', '127.0.0.1')}:"
            f"{os.getenv('ALLOYDB_PORT', '5432')}/"
            f"{os.getenv('ALLOYDB_DB', 'pragati')}"
        )
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def introspect_tables() -> list[dict]:
    """
    SELF-ASSEMBLY CORE: Discovers all user tables and their column metadata.
    Returns structured info the Cartographer agent uses to auto-register tools.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                t.table_name,
                array_agg(
                    json_build_object(
                        'column_name', c.column_name,
                        'data_type', c.data_type,
                        'is_nullable', c.is_nullable
                    )::text
                    ORDER BY c.ordinal_position
                ) AS columns
            FROM information_schema.tables t
            JOIN information_schema.columns c
                ON c.table_name = t.table_name
                AND c.table_schema = t.table_schema
            WHERE t.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
              AND t.table_name NOT IN ('mcp_tool_registry')
            GROUP BY t.table_name
            ORDER BY t.table_name
        """)
    result = []
    for row in rows:
        cols = [json.loads(c) for c in row["columns"]]
        result.append({
            "table_name": row["table_name"],
            "columns": cols,
        })
    return result


async def execute_query(sql: str, params: list | None = None) -> list[dict]:
    """Execute a safe read-only query and return results as dicts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params or []))
    return [dict(r) for r in rows]


async def get_row_count(table_name: str) -> int:
    """Get approximate row count for a table."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM " + table_name  # table_name is internal only
        )
    return row["cnt"]


async def generate_embedding(text: str) -> list[float]:
    """Generate a text embedding using Vertex AI text-embedding-004."""
    model = _get_embed_model()
    embeddings = model.get_embeddings([text])
    return embeddings[0].values


async def semantic_search(table: str, query_embedding: list[float], limit: int = 5) -> list[dict]:
    """Vector similarity search on a table's embedding column."""
    pool = await get_pool()
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    sql = f"""
        SELECT *, embedding <=> $1::vector AS distance
        FROM {table}
        WHERE embedding IS NOT NULL
        ORDER BY distance
        LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, vec_str, limit)
    return [dict(r) for r in rows]


async def register_tool_in_db(tool_name: str, source_table: str, description: str, columns: list) -> None:
    """Persist a newly registered MCP tool to the registry table."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mcp_tool_registry (tool_name, source_table, description, columns_json)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tool_name) DO UPDATE
            SET description = EXCLUDED.description,
                columns_json = EXCLUDED.columns_json,
                registered_at = NOW()
        """, tool_name, source_table, description, json.dumps(columns))


async def get_registered_tools() -> list[dict]:
    """Fetch all tools currently in the MCP registry."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mcp_tool_registry ORDER BY registered_at DESC"
        )
    return [dict(r) for r in rows]


async def increment_tool_call_count(tool_name: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE mcp_tool_registry SET call_count = call_count + 1 WHERE tool_name = $1",
            tool_name
        )
