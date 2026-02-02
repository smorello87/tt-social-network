# Data Architecture Recommendations

This document captures recommendations for improving data quality and making the network data more consistent and meaningful. Generated January 2026.

## Current State

- **3307 nodes** (persons and institutions)
- **4299 edges** (connections between nodes)
- Database: SQLite (`data/editor/network.db`)

---

## 1. Institution Subtypes

**Status: IMPLEMENTED**

Institutions now have a `subtype` column to categorize them:
- `magazine` - Periodicals (Il Carroccio, Divagando, Atlantica, etc.)
- `publisher` - Publishing houses (SF Vanni, Mondadori, etc.)
- `university` - Academic institutions (Columbia, Yale, Harvard, etc.)
- `organization` - Cultural/professional organizations (Casa Italiana, Italian Historical Society, etc.)
- `library` - Libraries (Library of Congress, NYPL, etc.)
- `film` - Film companies
- `prize` - Literary prizes

**Coverage:** 139 institutions categorized (90%+ of institution-related edges covered)

**Frontend:** Filter by subtype in the Nodes tab; edit subtype in node modal.

**Remaining work:** 162 institutions still uncategorized. Can be categorized incrementally via the editor UI.

---

## 2. Edge Type Refinement

**Status: NOT IMPLEMENTED (deferred)**

Currently all edges use generic types (`affiliation`, `personal`). More specific edge types would enable richer queries:

**Proposed edge types:**
- `contributor` - wrote for a publication
- `editor` - edited a publication
- `translator` - translated for/published by
- `board_member` - served on board
- `employee` - worked at institution
- `founder` - founded institution
- `student` - studied at university
- `professor` - taught at university
- `correspondent` - letter correspondence
- `collaborator` - creative collaboration
- `mentor` - mentorship relationship

**Why deferred:** Requires manual review of ~4000 edges to assign specific types. Could be done incrementally if provenance data is available.

---

## 3. Data Quality

**Status: IMPLEMENTED (fixes applied)**

Issues identified and resolved:
- **1 self-loop** - Node connected to itself (deleted)
- **85 bidirectional duplicates** - A→B and B→A for same relationship (duplicates deleted)

Remaining issue:
- **1 orphan node** - "Belfagor" (id 948) has no connections. May be intentional placeholder or error.
- **418 edges with type "unknown"** - Need review to assign proper type

**Ongoing maintenance:** Run periodic data quality checks via SQL:

```sql
-- Find self-loops
SELECT * FROM edges WHERE source_id = target_id;

-- Find bidirectional duplicates
SELECT e1.id, e2.id, n1.name as node1, n2.name as node2
FROM edges e1
JOIN edges e2 ON e1.source_id = e2.target_id AND e1.target_id = e2.source_id AND e1.id < e2.id
JOIN nodes n1 ON e1.source_id = n1.id
JOIN nodes n2 ON e1.target_id = n2.id;

-- Find orphan nodes
SELECT n.id, n.name, n.type FROM nodes n
LEFT JOIN edges e ON n.id = e.source_id OR n.id = e.target_id
WHERE e.id IS NULL;
```

---

## 4. Temporal Data

**Status: NOT IMPLEMENTED (challenging)**

Adding time ranges to edges would enable powerful queries:
- "Who was connected in 1925?"
- "How did the network evolve 1910-1940?"
- Animation of network growth over time

**Schema addition:**
```sql
ALTER TABLE edges ADD COLUMN start_year INTEGER;
ALTER TABLE edges ADD COLUMN end_year INTEGER;
```

**Why deferred:** Retrieving temporal data requires archival research for each relationship. Some sources (magazine contributor lists) have implicit date ranges that could be imported.

**Partial approach:** Start with data that already has dates:
- Divagando contributors (1945-1957 data in `contributors-and-board/`)
- Il Carroccio contributors (years often noted in contributor lists)
- University positions (often have date ranges)

---

## 5. Data Provenance

**Status: NOT IMPLEMENTED (deferred)**

Tracking where each data point came from would improve trust and enable verification:

**Schema addition:**
```sql
ALTER TABLE nodes ADD COLUMN source TEXT;
ALTER TABLE nodes ADD COLUMN source_url TEXT;
ALTER TABLE nodes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE edges ADD COLUMN source TEXT;
ALTER TABLE edges ADD COLUMN source_url TEXT;
ALTER TABLE edges ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

**Source examples:**
- `worldcat` - WorldCat import
- `divagando_toc` - Divagando table of contents
- `carroccio_contributors` - Il Carroccio contributor lists
- `omeka` - Omeka collection import
- `manual` - Manual entry

**Why deferred:** Requires backend changes and careful tracking during imports. Implement when starting new major imports.

---

## 6. Full Schema Proposal

**Status: NOT IMPLEMENTED (reference)**

Complete proposed schema for future implementation:

```sql
-- Nodes with full metadata
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    name_normalized TEXT,
    type TEXT NOT NULL CHECK(type IN ('person', 'institution')),
    subtype TEXT,
    birth_year INTEGER,
    death_year INTEGER,
    nationality TEXT,
    source TEXT,
    source_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edges with full metadata
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES nodes(id),
    target_id INTEGER NOT NULL REFERENCES nodes(id),
    type TEXT NOT NULL,
    subtype TEXT,
    start_year INTEGER,
    end_year INTEGER,
    source TEXT,
    source_url TEXT,
    confidence REAL DEFAULT 1.0,
    needs_review BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_nodes_subtype ON nodes(subtype);
CREATE INDEX idx_edges_type ON edges(type);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_years ON edges(start_year, end_year);
```

---

## Priority Order for Future Work

1. **Continue categorizing institutions** - 162 remaining, can be done via editor UI
2. **Review "unknown" edge types** - 418 edges need type assignment
3. **Add temporal data** - Start with sources that already have dates
4. **Implement provenance tracking** - Before next major import
5. **Refine edge types** - When provenance is established

---

## Network Analysis Insights

Key hubs in the network:
- **Il Carroccio** (971 connections) - Major magazine hub
- **Atlantica** (464 connections) - Successor publication
- **Divagando** (374 connections) - Italian magazine

Important bridge figures (connected to multiple major hubs):
- Giuseppe Prezzolini
- Agostino de Biasi
- Pietro Solari
- Emanuel Carnevali

These individuals are particularly significant for understanding cross-institutional connections in the Italian-American literary network.
