-- PRAGATI: India Health Intelligence Platform
-- AlloyDB Schema

CREATE EXTENSION IF NOT EXISTS vector;

-- Health indicators by state/district/year
CREATE TABLE IF NOT EXISTS health_indicators (
    id SERIAL PRIMARY KEY,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    value NUMERIC(12, 4) NOT NULL,
    unit VARCHAR(50),
    category VARCHAR(100),
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Health facilities
CREATE TABLE IF NOT EXISTS facilities (
    facility_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    facility_type VARCHAR(100),
    beds INTEGER,
    staff_count INTEGER,
    is_functional BOOLEAN DEFAULT TRUE,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Disease surveillance reports
CREATE TABLE IF NOT EXISTS disease_reports (
    report_id SERIAL PRIMARY KEY,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    disease VARCHAR(150) NOT NULL,
    cases INTEGER NOT NULL,
    deaths INTEGER DEFAULT 0,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- MCP tool registry (self-assembly metadata)
CREATE TABLE IF NOT EXISTS mcp_tool_registry (
    tool_id SERIAL PRIMARY KEY,
    tool_name VARCHAR(200) UNIQUE NOT NULL,
    source_table VARCHAR(100) NOT NULL,
    description TEXT,
    columns_json JSONB,
    registered_at TIMESTAMP DEFAULT NOW(),
    call_count INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_hi_state ON health_indicators(state);
CREATE INDEX IF NOT EXISTS idx_hi_indicator ON health_indicators(indicator_name);
CREATE INDEX IF NOT EXISTS idx_hi_year ON health_indicators(year);
CREATE INDEX IF NOT EXISTS idx_fac_state ON facilities(state);
CREATE INDEX IF NOT EXISTS idx_dr_state ON disease_reports(state);
CREATE INDEX IF NOT EXISTS idx_dr_disease ON disease_reports(disease);
CREATE INDEX IF NOT EXISTS idx_dr_year ON disease_reports(year);
