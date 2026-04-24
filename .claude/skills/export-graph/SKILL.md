---
name: export-graph
description: Export an LLM run graph or multi-run overlay as a Mermaid diagram, interactive HTML, or JSON. Use when the user wants to visualize a captured run, share a graph, or export run data for external analysis.
argument-hint: "[run-id | 'overlay' run-id...] [--format mermaid|html|json]"
metadata:
  authors:
    - thomas.haid@dynatrace.com
---

# Export Run Graph

Export a captured LLM run graph from the agent-run-optimizer project in a visual or machine-readable format.

## Step 1 — Parse Arguments

- Single run ID → export one RunGraph
- Multiple run IDs or `overlay` keyword → build an overlay graph first, then export
- `--format` flag determines output; default is `mermaid`

## Step 2 — Load Run Data

Check for run data in this order:
1. SQLite: query `runs.db` → `SELECT * FROM runs WHERE run_id = ?`
2. JSON fallback: read `runs/{run-id}.json`

If the run does not exist, list available run IDs and ask the user to pick one.

## Step 3 — Build Output

### Mermaid Format

Generate a `flowchart TD` diagram. Each node label must include:
- Node type icon: 🤖 for LLM, 🔧 for tool, 👤 for human
- Model name (LLM nodes) or tool name (tool nodes)
- Token counts and latency
- ✓ / ✗ for terminal success/failure nodes

```
flowchart TD
    N1["🤖 claude-opus-4-7\nin: 1,234 · out: 456\n120ms"] --> N2
    N2["🔧 search\nlatency: 230ms"] --> N3
    N3["🤖 claude-opus-4-7\nin: 890 · out: 120\n95ms · ✓"]
```

For overlay graphs, annotate edges with run frequency: `-->|3/5 runs|`.

### HTML Format

Generate a self-contained HTML file using D3.js (bundled inline, no CDN):
- Force-directed graph layout
- Node tooltip showing truncated context (200 chars max)
- Color coding: blue=LLM, green=tool, orange=human, red=failed
- Edge thickness proportional to run frequency in overlays

Write to `exports/{run-id}.html`.

### JSON Format

Export the raw RunGraph as pretty-printed JSON.
Write to `exports/{run-id}.json`.

## Step 4 — Output Results

- **Mermaid**: print the fenced code block directly so the IDE renders it inline
- **HTML**: write file, report path
- **JSON**: write file, report path

## Quality Check

Before reporting done:
- Mermaid: scan for unclosed brackets or invalid node IDs
- HTML: confirm the `<script>` block is self-contained (no `src=` referencing external URLs)
- JSON: verify with `python -m json.tool` or equivalent