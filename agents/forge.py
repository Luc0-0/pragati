"""
PRAGATI - Forge Agent
Takes the data map from Cartographer and forges (creates) MCP tool definitions.
This is the "self-assembly" heart of PRAGATI.
"""
from mcp import tool_registry


async def forge_tools(landscape: dict) -> list[dict]:
    """
    For each discovered table, forge an MCP tool definition and register it.
    Returns the list of all registered tools.
    """
    print(f"Forge: Forging tools for {landscape['summary']['total_tables']} tables...")
    registered = []

    for table_info in landscape["tables"]:
        tool = await tool_registry.register_tool(
            table_name=table_info["table_name"],
            columns=table_info["columns"],
        )
        registered.append(tool)
        print(f"  Forged: {tool['name']}")

    print(f"Forge: {len(registered)} tools created and registered.")
    return registered


def get_tool_for_query(query: str) -> str | None:
    """
    Simple intent routing: match a natural language query to the best tool.
    Returns the tool name or None.
    """
    q = query.lower()

    # Priority scoring
    scores = {}
    for tool in tool_registry.get_all_tools():
        score = 0
        table = tool["source_table"]

        if table == "health_indicators":
            keywords = ["mortality", "imr", "mmr", "immunization", "vaccine", "delivery",
                        "stunting", "anaemia", "anemia", "tb", "contraceptive", "anc",
                        "indicator", "rate", "coverage", "nutrition", "health indicator"]
        elif table == "facilities":
            keywords = ["hospital", "phc", "chc", "facility", "facilities", "bed", "staff",
                        "clinic", "centre", "center", "doctors", "nurses", "infrastructure"]
        elif table == "disease_reports":
            keywords = ["malaria", "dengue", "disease", "outbreak", "cases", "deaths",
                        "tuberculosis", "typhoid", "diarrhea", "covid", "epidemic",
                        "chikungunya", "cholera", "report", "surveillance"]
        else:
            keywords = [table.replace("_", " ")]

        for kw in keywords:
            if kw in q:
                score += 2
        if table.replace("_", " ") in q:
            score += 5

        scores[tool["name"]] = score

    if not scores:
        return None

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else list(scores.keys())[0]  # fallback to first tool


def determine_query_type(tool_name: str, query: str) -> tuple[str, str | None, str | None]:
    """
    Determine the best query_type and parameters from a natural language query.
    Returns (query_type, param1, param2).
    """
    q = query.lower()
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        return "all", None, None

    table = tool["source_table"]

    # Extract state name
    STATES = [
        "uttar pradesh", "maharashtra", "bihar", "west bengal", "rajasthan",
        "tamil nadu", "karnataka", "gujarat", "madhya pradesh", "andhra pradesh",
    ]
    detected_state = next((s.title() for s in STATES if s in q), None)

    if table == "health_indicators":
        # Detect indicator
        INDICATORS = {
            "imr": "Infant Mortality Rate",
            "infant mortality": "Infant Mortality Rate",
            "mmr": "Maternal Mortality Ratio",
            "maternal mortality": "Maternal Mortality Ratio",
            "immunization": "Full Immunization Coverage",
            "vaccine": "Full Immunization Coverage",
            "stunting": "Stunting Prevalence",
            "anaemia": "Anaemia in Women",
            "anemia": "Anaemia in Women",
            "tb": "TB Detection Rate",
            "tuberculosis": "TB Detection Rate",
            "malaria api": "Malaria API",
            "contraceptive": "Contraceptive Prevalence Rate",
            "anc": "ANC Coverage",
        }
        detected_indicator = next((v for k, v in INDICATORS.items() if k in q), None)

        if "compare" in q or "vs" in q or "versus" in q or "across state" in q:
            return "compare_states", detected_indicator or "Infant Mortality Rate", None
        if "trend" in q or "over time" in q or "year" in q:
            return "trend", detected_state or "Maharashtra", detected_indicator or "Infant Mortality Rate"
        if detected_indicator:
            return "by_indicator", detected_indicator, None
        if detected_state:
            return "by_state", detected_state, None
        return "all", None, None

    elif table == "facilities":
        FTYPES = {"phc": "PHC", "chc": "CHC", "hospital": "District Hospital",
                  "sub-centre": "Sub-Centre", "sub centre": "Sub-Centre"}
        detected_type = next((v for k, v in FTYPES.items() if k in q), None)

        if "summary" in q or "how many" in q or "count" in q or "total" in q:
            return "summary", None, None
        if detected_type:
            return "by_type", detected_type, None
        if detected_state:
            return "by_state", detected_state, None
        return "all", None, None

    elif table == "disease_reports":
        DISEASES = ["malaria", "dengue", "tuberculosis", "typhoid", "diarrhea",
                    "covid", "chikungunya", "cholera", "leptospirosis"]
        detected_disease = next((d.title() for d in DISEASES if d in q), None)

        if "hotspot" in q or "worst" in q or "highest" in q or "top" in q:
            # Try to extract year
            import re
            year_match = re.search(r"\b(202[0-9])\b", q)
            year = int(year_match.group()) if year_match else 2024
            return "hotspots", str(year), None
        if "trend" in q or "over time" in q:
            return "trend", detected_disease or "Malaria", detected_state or "Maharashtra"
        if detected_disease and detected_state:
            return "by_state", detected_state, None
        if detected_disease:
            return "by_disease", detected_disease, None
        if detected_state:
            return "by_state", detected_state, None
        return "all", None, None

    return "all", None, None
