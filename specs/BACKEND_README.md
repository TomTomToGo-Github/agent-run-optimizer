# Backend — Architecture and Usage

## Overview

The backend is a pure-Python library (`src/agent_run_optimizer/`) organised into the following modules:

```
src/agent_run_optimizer/
  graph/models.py    — RunNode, RunEdge, RunPath, RunGraph (shared node pool)
  storage/           — YAMLRunStore (primary), RunStoreBase ABC, schema serialisation
  capture/           — RunCapture ctx mgr, OTel exporter, LangChain callback (planned)
  analysis/          — compare, stats, patterns, fixpoint detection (planned)
  viz/html.py        — Cytoscape.js interactive HTML visualisation
  cli.py             — ai-repro CLI (planned)
hooks/capture_hook.py — Claude Code hook script (planned, see docs/HOOKS.md)
runs/                — YAML run files (committed to git)
exports/             — generated HTML exports (gitignored)
```

**Implemented today:** `graph/`, `storage/`, `viz/html.py`, `run_example.py`
**Planned:** `capture/`, `analysis/`, `cli.py`, `hooks/` — see `specs/BACKEND_MISSING.md`

---

## Data Model (`graph/models.py`)

### `RunGraph`
Top-level container for one test case. Holds a shared node pool and a list of paths.

```python
class RunGraph(BaseModel):
    test_case_id: str
    description:  str
    created_at:   datetime | None
    tags:         list[str]
    nodes:        dict[str, RunNode]   # node_id → RunNode
    paths:        list[RunPath]
```

### `RunNode`
A single step in a run — an LLM call, tool invocation, human interaction, or checkpoint.

```python
class RunNode(BaseModel):
    id:             str
    type:           NodeType           # llm | tool | human | checkpoint
    label:          str
    is_fixpoint:    bool = False       # every successful path must pass through this node
    user_important: bool = False       # toggled in the UI; persisted via sync
    metadata:       dict[str, Any]     # model, latency_ms, tokens, tool args, etc.
```

**Node flags:**
- `is_fixpoint` — marks a required step every successful path must cross. Set manually in the YAML or (once implemented) automatically via `ai-repro fixpoints --update`.
- `user_important` — toggled interactively in the HTML viz; written back to the YAML store when the Sync button is pressed.

**Standard `metadata` keys** (all optional; populated by the capture layer):

| Key | Node types | Description |
|---|---|---|
| `model` | llm | Model identifier, e.g. `claude-opus-4-7` |
| `messages_hash` | llm | SHA-256 of the serialised message list |
| `messages` | llm | Full message list (`null` if `store_messages=False`) |
| `input_tokens` | llm | Prompt token count |
| `output_tokens` | llm | Completion token count |
| `cost_usd` | llm | Estimated cost (`null` if not available) |
| `latency_ms` | all | Wall-clock duration of the call |
| `estimated` | all | `true` if any metric was estimated rather than measured |
| `tool` | tool | Tool name |
| `args` | tool | Tool input arguments |
| `result` | tool | Tool output (`null` if `store_tool_results=False`) |
| `otel_span_id` | all | OTel span ID for cross-system tracing |
| `otel_trace_id` | all | OTel trace ID |

### `RunPath`
One execution trace — an ordered sequence of node IDs and the edges between them.

```python
class RunPath(BaseModel):
    path_id:       str
    outcome:       str               # success | failure | partial | unknown
    timestamp:     datetime | None
    duration_ms:   int | None
    node_sequence: list[str]         # ordered node IDs
    edges:         list[RunEdge]
    metadata:      dict[str, Any]
```

### `RunEdge`
A directed connection between two nodes.

```python
class RunEdge(BaseModel):
    source: str
    target: str
    type:   EdgeType    # sequential | conditional | retry | parallel
    label:  str
```

---

## Storage Layer

### Abstract interface (`storage/base.py`)

```python
class RunStoreBase(ABC):
    def load(self, test_case_id: str) -> RunGraph: ...
    def save(self, graph: RunGraph) -> None: ...
    def sync_node_states(self, test_case_id: str, updates: dict[str, dict]) -> None: ...
    def list_test_cases(self) -> list[str]: ...
```

**Switching backends requires changing exactly one line in `run_example.py`.**

### YAML store (`storage/yaml_store.py`)

```python
store = YAMLRunStore(runs_dir="runs")

graph = store.load("incident-resolution")      # reads runs/incident-resolution.yaml
store.save(graph)                               # writes back (full overwrite)
store.sync_node_states("incident-resolution",  # patch specific node fields only
    {"llm-initial": {"user_important": True}})
store.list_test_cases()                         # → ["incident-resolution", ...]
```

YAML file naming: `{test_case_id}.yaml` — the `test_case.id` field inside the file must match the filename stem.

### YAML file format (`storage/schema.py`)

```yaml
_schema_version: "1"
test_case:
  id: incident-resolution
  description: "..."
  created_at: "2026-04-23"
  tags: [demo]

nodes:
  llm-initial:
    type: llm
    label: "Analyze Incident"
    is_fixpoint: true
    user_important: false
    metadata:
      model: claude-opus-4-7
      avg_latency_ms: 1250

paths:
  - path_id: run-001
    outcome: success
    duration_ms: 5790
    node_sequence: [llm-initial, tool-search, llm-resolve, llm-verify]
    edges:
      - {from: llm-initial, to: tool-search}
      ...
```

---

## Capture Usage (`capture/context.py`)

> **Planned — not yet implemented.** See `specs/BACKEND_MISSING.md`.

```python
from agent_run_optimizer.capture.context import RunCapture

with RunCapture(task_id="my-task") as run:
    node = run.add_llm_node(model="claude-opus-4-7", messages=[...])
    run.add_tool_node(tool_name="search", args={"q": "..."}, result="...")
# → appends a new path to runs/my-task.yaml
```

For automatic capture via Claude Code hooks (no code changes needed), see `docs/HOOKS.md`.

---

## Visualization (`viz/html.py`)

```python
from agent_run_optimizer.viz.html import HtmlViz

html: str = HtmlViz().generate_html(graph)
# Write to file for static export:
Path("output.html").write_text(html, encoding="utf-8")
```

`HtmlViz` is stateless; call `generate_html` multiple times without side effects.

---

## Example Runner (`run_example.py`)

```python
from agent_run_optimizer.storage.yaml_store import YAMLRunStore
from agent_run_optimizer.viz.html import HtmlViz
from run_example import serve_and_open

store = YAMLRunStore("runs")
serve_and_open(test_case_id="incident-resolution", store=store, port=8765)
```

The server exposes:
- `GET /` — rendered HTML
- `POST /api/sync` — `{ test_case_id, updates }` → `store.sync_node_states()`