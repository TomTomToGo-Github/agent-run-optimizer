# Implementation Plan

> **Design decisions recorded here** so the rationale travels with the plan.

---

## Design Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Message storage | `messages_hash` (full SHA-256, `sha256:` prefix) always stored; full `messages` stored only when `store_messages=True` (default `True`) | Hash enables dedup/identity without content; flag is explicit privacy opt-out |
| Storage format | YAML files — one file per test case (`runs/{task-id}.yaml`), one path section per run | Human-readable, git-committable, diffs cleanly, no DB setup needed |
| Capture strategy | OTel as the unifying integration layer; Claude Code hooks first, LangChain second, others deferred | OTel spans are common currency; Claude Code hooks need zero agent code changes |
| Claude Code LLM nodes | Use `PreToolUse` + `PostToolUse` + `Stop` hooks together; reconstruct LLM turns from `Stop` conversation history | Maximum completeness; token counts estimated when not available in payload |
| Task naming | `AI_REPRO_TASK` env var → `task_id=` kwarg on `RunCapture` → calling function name | Task-based; env var covers harness/CLI; kwarg covers library usage |
| Async | `BatchSpanProcessor` queues spans; `force_flush()` on `RunCapture` exit drains queue before writing | Data completeness over immediacy; no loss even in fully async workflows |
| Replay | Contextual — restore checkpoint state, continue with live LLM calls | Simpler than deterministic mock replay; replay recorded as new path with `parent_path_id` |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│              Capture Sources                                     │
│  Claude Code hooks │ GitHub Copilot │ LangChain callbacks        │
└────────────┬───────────────┬────────────────┬────────────────────┘
             │               │                │
             ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│              OpenTelemetry Layer                                  │
│   Each source emits OTel spans → our RunSpanExporter captures    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│              Core Data Model                                      │
│   RunNode  RunEdge  RunGraph  RunPath  RunCaptureConfig           │
└──────────────┬───────────────────────────────┬───────────────────┘
               │ persist                        │ query / analyze
┌──────────────▼──────────────┐  ┌─────────────▼──────────────────┐
│  YAML Store                 │  │  Graph Engine (networkx)         │
│  runs/{test-case}.yaml      │  │  overlay / compare / stats       │
│  one file per test case     │  └─────────────┬──────────────────┘
│  one section per path/run   │                │
└─────────────────────────────┘  ┌─────────────▼──────────────────┐
                                  │  Visualization / CLI            │
                                  │  rich  mermaid  html  cli       │
                                  └────────────────────────────────┘
```

---

## YAML Storage Format

One file per test case. Each run of that test case adds a path entry.

```yaml
# runs/my-agent-task.yaml

test_case:
  id: my-agent-task
  description: "Agent resolves an incident using search and read tools"
  created_at: "2026-04-23"
  tags: [experiment-a]

paths:
  - path_id: run-001
    timestamp: "2026-04-23T10:00:00Z"
    outcome: success
    duration_ms: 5230
    total_input_tokens: 2345
    total_output_tokens: 678
    total_cost_usd: 0.023
    otel_trace_id: "4bf92f3577b34da6a3ce929d0e0e4736"
    nodes:
      - id: n-001
        type: llm
        timestamp: "2026-04-23T10:00:01Z"
        inputs:
          model: claude-opus-4-7
          temperature: 1.0
          messages_hash: "sha256:abc123def456..."
          messages: null            # null when store_messages=False
          tools_available: [search, read_file]
        outputs:
          response: "I'll search for that..."
          stop_reason: tool_use
          tool_calls:
            - tool: search
              args: {query: "latest alerts"}
        metadata:
          input_tokens: 1234
          output_tokens: 456
          latency_ms: 1200
          cost_usd: 0.012
          otel_span_id: "00f067aa0ba902b7"
      - id: n-002
        type: tool
        timestamp: "2026-04-23T10:00:02Z"
        inputs:
          tool: search
          args: {query: "latest alerts"}
        outputs:
          result: "[Alert] CPU spike on host-42"
        metadata:
          latency_ms: 230
          otel_span_id: "a2fb4a1d1a96d312"
    edges:
      - {from: n-001, to: n-002}
      - {from: n-002, to: n-003}

  - path_id: run-002
    timestamp: "2026-04-23T10:15:00Z"
    outcome: failure
    # ... same structure, different path
```

**Key properties:**
- `messages_hash` — always computed (SHA-256 of serialized message list), stored regardless of flag
- `messages` — full list stored only if `RunCaptureConfig.store_messages = True`; otherwise `null`
- `otel_trace_id` / `otel_span_id` — preserved so runs are traceable in external OTel backends

---

## Phase 1 — Core Data Model

**Goal**: Immutable data structures everything else builds on.

### Deliverables

`src/agent_run_optimizer/graph/models.py`:

```python
class NodeType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    HUMAN = "human"
    CHECKPOINT = "checkpoint"

class RunCaptureConfig(BaseModel):
    store_messages: bool = True      # if False, messages stored as null
    store_tool_results: bool = True  # if False, tool outputs stored as null
    cost_per_1k_tokens: dict = {}    # model → (input_cost, output_cost)

class LLMInputs(BaseModel):
    model: str
    temperature: float | None = None
    messages_hash: str               # always present
    messages: list[dict] | None      # None if store_messages=False
    tools_available: list[str] = []
    system_prompt_hash: str | None = None
    system_prompt: str | None = None

class ToolInputs(BaseModel):
    tool: str
    args: dict
    result: Any | None               # None if store_tool_results=False

class RunNode(BaseModel):
    id: str                          # UUID
    type: NodeType
    timestamp: datetime
    inputs: LLMInputs | ToolInputs | dict
    outputs: dict
    metadata: dict                   # tokens, latency_ms, cost_usd, otel_span_id, ...
    outcome: Literal["success", "failure", "partial", "unknown"] = "unknown"

class RunEdge(BaseModel):
    source: str
    target: str
    label: str = ""

class RunGraph(BaseModel):           # wraps networkx DiGraph
    run_id: str
    test_case_id: str
    created_at: datetime
    outcome: str = "unknown"
    tags: list[str] = []
    otel_trace_id: str | None = None
    # nodes/edges managed via networkx internally
```

`src/agent_run_optimizer/graph/overlay.py`:
- `overlay(graphs: list[RunGraph]) -> RunGraph` — merges N graphs, adds `_run_count` and `_frequency` metadata to edges

`tests/test_models.py` — unit tests

### Open Questions
- `messages_hash`: SHA-256 of `json.dumps(messages, sort_keys=True)`? Or a shorter hash? SHA-256 truncated to 16 hex chars is readable and collision-safe.
- Should `RunCaptureConfig` be global (singleton) or per-capture-session?

---

## Phase 2 — YAML Storage

**Goal**: Persist and retrieve RunGraphs as human-readable YAML files.

### Deliverables

`src/agent_run_optimizer/storage/yaml_store.py` — `YAMLRunStore`:
- Storage directory: `runs/` (configurable)
- File naming: `{test_case_id}.yaml` — one file per test case
- `save(graph: RunGraph)` — appends a new path section to the existing file (or creates it)
- `load(test_case_id: str) -> list[RunGraph]` — loads all paths for a test case
- `load_path(test_case_id: str, path_id: str) -> RunGraph` — loads one path
- `list_test_cases() -> list[str]`
- `delete_path(test_case_id: str, path_id: str)`
- Schema version header: `_schema_version: "1"` in each file — allows future migration

`src/agent_run_optimizer/storage/base.py` — `RunStoreBase` ABC

`src/agent_run_optimizer/storage/schema.py` — YAML serialization helpers:
- `RunGraph → dict` and `dict → RunGraph`
- Version-aware loader (reads `_schema_version`, applies migrations)

### Schema Versioning Strategy
- Every YAML file carries `_schema_version: "1"` at the top
- `schema.py` has a `MIGRATIONS: dict[str, callable]` — `{"1→2": migrate_v1_to_v2}`
- On load: detect version, apply chain of migrations, return current model
- Old files are never written back automatically (migration is explicit)
- This keeps files readable in both old and new format until explicitly migrated

### Open Questions
- For large test cases (100+ paths), YAML files can get large. Append-only write is O(1); full re-parse on read is O(n paths). Acceptable for now; add an optional SQLite index if search becomes slow.
- YAML append strategy: read-parse-append-write is safe for sequential use. For concurrent writes (parallel test runs), use file locking (`filelock` library).

---

## Phase 3 — OTel Capture Layer

**Goal**: Intercept LLM and tool calls from any source by treating OTel spans as the universal integration bus.

### Architecture

```
Source                          →  OTel span emitted     →  Our exporter  →  RunNode
──────────────────────────────────────────────────────────────────────────────────────
Claude Code hook (post-tool)    →  span(tool_call)        →  ToolNode
Claude Code hook (pre/post msg) →  span(llm_call)         →  LLMNode
LangChain on_llm_end callback   →  span(llm_call)         →  LLMNode
LangChain on_tool_end callback  →  span(tool_call)        →  ToolNode
Direct anthropic SDK call       →  span(llm_call)         →  LLMNode  (optional adapter)
```

### Deliverables

`src/agent_run_optimizer/capture/otel_exporter.py` — `RunSpanExporter`:
- Implements `opentelemetry.sdk.trace.export.SpanExporter`
- `export(spans)` → converts each completed span to a `RunNode`, adds to active `RunGraph`
- Span attribute conventions (what to put in each OTel span so the exporter can parse it):
  ```
  ai.type              = "llm" | "tool" | "human"
  ai.model             = "claude-opus-4-7"
  ai.input_tokens      = 1234
  ai.output_tokens     = 456
  ai.messages_hash     = "sha256:abc..."
  ai.messages_json     = "<json>" | omit if store_messages=False
  ai.tool_name         = "search"
  ai.tool_args_json    = "<json>"
  ai.tool_result_json  = "<json>" | omit if store_tool_results=False
  ai.cost_usd          = 0.012
  ai.outcome           = "success" | "failure" | "unknown"
  ```

`src/agent_run_optimizer/capture/claude_code_hooks.py` — Claude Code integration:
- A settings.json hooks template that fires on Claude Code's `PostToolUse` and `Stop` events
- Hook script (`hooks/capture_hook.py`) that receives hook payload → emits OTel span → written to YAML
- Works with Claude Code's hook system (shell script or Python script called by the harness)
- No modification to the agent code needed — purely external instrumentation

`src/agent_run_optimizer/capture/langchain_callback.py` — LangChain integration:
- `ReproducibilityCallbackHandler(BaseCallbackHandler)` — implements `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`
- Each callback emits an OTel span with the `ai.*` attributes above
- Usage: `agent.run(..., callbacks=[ReproducibilityCallbackHandler()])`

`src/agent_run_optimizer/capture/context.py` — `RunCapture` context manager:
- `with RunCapture(test_case_id="my-task", store=..., config=RunCaptureConfig(...)) as run:`
- Registers the `RunSpanExporter` with the OTel `TracerProvider`
- On exit: finalizes graph, saves to YAML store

### Async Handling
- All span exporters in OTel are synchronous by default — spans are buffered and flushed
- For async LLM calls: use `BatchSpanProcessor` with a queue; the processor drains the queue in a background thread
- `RunCapture.__aexit__` calls `force_flush()` on the provider — waits until all pending spans are exported before writing
- This ensures no data loss even if the calling code is fully async

### Claude Code Hook Integration (Example)

`.claude/settings.json` addition:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [{"type": "command", "command": "python hooks/capture_hook.py post-tool"}]
      }
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}
    ]
  }
}
```

The hook script receives JSON on stdin with the tool name, inputs, outputs, and timing — exactly what we need for a `ToolNode`.

### Capture Strategy for LLM Nodes (resolved)

Claude Code's `PreToolUse`/`PostToolUse` hooks give us clean tool nodes. For LLM nodes there is no per-message hook. **Resolved approach**: use all three hooks together:

1. `PreToolUse` — records the conversation state *before* the tool call (= full input context to the LLM that decided to call this tool)
2. `PostToolUse` — records tool result and timing
3. `Stop` — contains the complete final message history; walk the turns to reconstruct each LLM call as a node

Token counts are not available in hook payloads → stored as `null` and `metadata.estimated = true`. The Anthropic token-counting endpoint can optionally be called to fill these in post-hoc.

GitHub Copilot has no public callback API → deferred; focus on Claude Code first.

---

## Phase 4 — Graph Analysis

**Goal**: Extract insights from stored runs.

### Deliverables

`src/agent_run_optimizer/analysis/compare.py`:
- `compare_paths(path_a, path_b) -> PathDiff`
- `PathDiff`: first divergence index, divergence type (different tool, different model response hash, extra step, missing step)

`src/agent_run_optimizer/analysis/stats.py`:
- `run_stats(graphs: list[RunGraph]) -> RunStats`
- `RunStats`: per-metric distributions (mean/p50/p95/p99), success rate, path frequency table

`src/agent_run_optimizer/analysis/patterns.py`:
- `find_common_paths(graphs) -> list[(RunPath, count)]`
- `find_divergence_nodes(overlay_graph) -> list[RunNode]` — nodes with out-degree > 1 in overlay

---

## Phase 5 — Visualization

### Deliverables

`src/agent_run_optimizer/viz/terminal.py` — `rich` tree/panel:
- `show_run(graph)` — single run as a rich tree
- `show_overlay(graph)` — overlay with edge frequency labels

`src/agent_run_optimizer/viz/mermaid.py`:
- `to_mermaid(graph) -> str`
- Overlay-aware: `-->|3/5 runs|` on edges

`src/agent_run_optimizer/viz/html.py`:
- `to_html(graph, path)` — self-contained D3.js file, no CDN

---

## Phase 6 — CLI

### Deliverables

`src/agent_run_optimizer/cli.py` — Click CLI, entry point `ai-repro`:

```
ai-repro list [--tag <tag>]
ai-repro show <test-case-id> [--run <path-id>] [--format terminal|mermaid]
ai-repro compare <test-case-id> <path-id-a> <path-id-b>
ai-repro overlay <test-case-id> [--export html|mermaid]
ai-repro export <test-case-id> [--run <path-id>] --format mermaid|html|json
ai-repro replay <test-case-id> <path-id> [--from <node-id>]
ai-repro stats <test-case-id>
ai-repro tag <test-case-id> <path-id> <tag>
```

`pyproject.toml` entry point:
```toml
[project.scripts]
ai-repro = "agent_run_optimizer.cli:cli"
```

---

## Phase 7 — Checkpointed Replay (Contextual)

**Goal**: Re-run an agent from any saved checkpoint node with live LLM calls, restoring context to match that point.

### Deliverables

`src/agent_run_optimizer/capture/checkpoint.py`:
- `@checkpoint(label="stage-2")` decorator — serializes function args + return value as a `CHECKPOINT` node in the active run
- `CheckpointState`: the serialized args/kwargs at that point in the graph

`src/agent_run_optimizer/replay.py`:
- `replay(test_case_id, path_id, from_node_id=None)`
- If `from_node_id` given: load the checkpoint state at that node, restore context, continue with live LLM calls
- The resumed execution is recorded as a new path in the same YAML file, with `parent_path_id` pointing to the source path and `resumed_from_node` set

### What This Enables
- Run an expensive 5-step workflow; it fails at step 4
- Fix the prompt for step 4; replay from step 3's checkpoint (not step 1)
- New path is saved alongside the original — full audit trail preserved

---

## Phase 8 — Integrations (Future)

| Integration | Status | Notes |
|---|---|---|
| Claude Code hooks | Phase 3 | Primary target |
| LangChain callbacks | Phase 3 | `ReproducibilityCallbackHandler` |
| GitHub Copilot | Deferred | No public callback API; VS Code extension required |
| Direct Anthropic SDK | Deferred | Context manager wrap; lower priority than harness capture |
| PostgreSQL backend | Deferred | SQLite index for YAML store if scale demands it |
| OpenAI SDK | Deferred | Same OTel span pattern |
| PII redaction | Deferred | Hook in `RunSpanExporter` before node is written |
| Embeddings for node similarity | Deferred | Semantic dedup for overlay coarsening |

---

## Target File Structure

```
agent-run-optimizer/
├── src/
│   └── agent_run_optimizer/
│       ├── __init__.py
│       ├── graph/
│       │   ├── models.py          # RunNode, RunEdge, RunGraph, RunPath, RunCaptureConfig
│       │   └── overlay.py         # overlay(graphs) -> RunGraph
│       ├── storage/
│       │   ├── base.py            # RunStoreBase ABC
│       │   ├── yaml_store.py      # YAMLRunStore (primary)
│       │   └── schema.py          # serialization + schema versioning
│       ├── capture/
│       │   ├── otel_exporter.py   # RunSpanExporter (OTel SpanExporter)
│       │   ├── claude_code_hooks.py  # OTel bridge for Claude Code hook payloads
│       │   ├── langchain_callback.py # ReproducibilityCallbackHandler
│       │   ├── context.py         # RunCapture context manager
│       │   └── checkpoint.py      # @checkpoint, CheckpointState
│       ├── analysis/
│       │   ├── compare.py         # compare_paths, PathDiff
│       │   ├── stats.py           # run_stats, RunStats
│       │   └── patterns.py        # find_common_paths, find_divergence_nodes
│       ├── viz/
│       │   ├── terminal.py        # rich display
│       │   ├── mermaid.py         # to_mermaid()
│       │   └── html.py            # to_html()
│       ├── replay.py              # replay()
│       └── cli.py                 # Click CLI entry point
├── hooks/
│   └── capture_hook.py            # Claude Code hook script (reads stdin JSON → OTel span)
├── runs/                          # YAML run files (git-committed)
│   └── .gitkeep
├── exports/                       # generated HTML/mermaid exports (gitignored)
└── tests/
    ├── test_models.py
    ├── test_storage.py
    ├── test_capture.py
    ├── test_analysis.py
    └── test_viz.py
```

---

## Recommended Starting Point

1. `graph/models.py` — data model with `messages_hash`/`messages` split
2. `storage/yaml_store.py` + `storage/schema.py` — YAML read/write with schema versioning
3. `capture/otel_exporter.py` — `RunSpanExporter` converting OTel spans to RunNodes
4. `capture/claude_code_hooks.py` + `hooks/capture_hook.py` — first real capture source
5. `viz/terminal.py` + `viz/mermaid.py` — make runs visible
6. `cli.py` with `list`, `show`, `export` commands

At this point: run an agent with Claude Code, capture the run via hooks, view the graph. Everything after is analysis and additional integrations.

---

## Resolved Decisions (from design discussion)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | `messages_hash` format | Full SHA-256, 64 hex chars, prefixed `sha256:` | Collision-proof beats YAML readability; prefix makes format self-describing |
| 2 | Task / test case naming | `AI_REPRO_TASK` env var → `task_id=` kwarg on `RunCapture` → function name as last resort | Task-based identity; env var works for harness/CLI usage; kwarg works for library usage |
| 3 | Claude Code LLM node capture | Use **all available hooks** (`PreToolUse`, `PostToolUse`, `Stop`); reconstruct LLM nodes by walking the full conversation history from the `Stop` payload; cross-reference with tool hook timings | Goal is maximum completeness; gaps (e.g. token counts not in hook payload) filled with estimates and flagged via `metadata.estimated = True` |
| 4 | `store_messages` default | `True` — full capture by default | Easiest to debug; users who need privacy opt out explicitly via `RunCaptureConfig(store_messages=False)` |
| 5 | Async handling | `BatchSpanProcessor` queues spans; `force_flush()` called on `RunCapture` exit to drain queue before writing | Data completeness over immediacy; no data loss even in fully async workflows |
| 6 | Replay mode | Contextual — restore state at checkpoint, continue with live LLM calls; replay recorded as a new path with `parent_path_id` + `resumed_from_node` | Simpler than mock-based deterministic replay; preserves full audit trail |
| 7 | Primary capture target | Claude Code hooks first, LangChain second; GitHub Copilot deferred (no public callback API) | Claude Code hooks are the most accessible integration point with no agent code changes required |