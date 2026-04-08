"""
PRAGATI - Cartographer Agent
Discovers and maps the available data landscape in AlloyDB.
Produces a structured "data map" used by the Forge to create tools.
"""
import asyncio
from db import alloydb_client as db


async def discover_data_landscape() -> dict:
    """
    Introspects AlloyDB and returns a rich data map:
    - Tables and their schemas
    - Row counts
    - Sample values for key columns
    """
    print("Cartographer: Mapping data landscape...")
    tables = await db.introspect_tables()

    landscape = {"tables": [], "summary": {}}

    for table in tables:
        table_name = table["table_name"]
        try:
            row_count = await db.get_row_count(table_name)
        except Exception:
            row_count = -1

        # Get distinct values for categorical string columns (for tool hints)
        sample_values = {}
        for col in table["columns"]:
            if col["data_type"] in ("character varying", "text") and col["column_name"] not in ("name", "embedding"):
                try:
                    rows = await db.execute_query(
                        f"SELECT DISTINCT {col['column_name']} FROM {table_name} LIMIT 10"
                    )
                    sample_values[col["column_name"]] = [r[col["column_name"]] for r in rows]
                except Exception:
                    pass

        landscape["tables"].append({
            "table_name": table_name,
            "columns": table["columns"],
            "row_count": row_count,
            "sample_values": sample_values,
        })

    landscape["summary"] = {
        "total_tables": len(landscape["tables"]),
        "total_rows": sum(t["row_count"] for t in landscape["tables"] if t["row_count"] > 0),
        "table_names": [t["table_name"] for t in landscape["tables"]],
    }

    print(f"Cartographer: Mapped {landscape['summary']['total_tables']} tables, "
          f"{landscape['summary']['total_rows']} total rows")
    return landscape
