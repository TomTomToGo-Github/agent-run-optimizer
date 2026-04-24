# Backend — Missing / Planned Features

Organised by the phases in `PLAN.md`. Stub `__init__.py` files exist for `capture/` and `analysis/` but contain no implementation.

---

## Graph Layer (`graph/`)

### `graph/overlay.py` — not started
- `overlay(graphs: list[RunGraph]) -> RunGraph` — merge N graphs into one weighted graph
- Node identity: same `(type, model/tool_name)` → same overlay node
- Edge `metadata["run_count"]` and `metadata["frequency"]` for thickness/opacity in the UI
- `find_divergence_nodes(overlay_graph)` — nodes with out-degree > 1

### `RunGraph` — networkx integration — not started
- Internal `nx.DiGraph` behind `RunGraph` for path traversal, shortest path, cycle detection
- `RunGraph.to_networkx()` helper
- Required by `analysis/` and `overlay.py`

---

## Storage Layer (`storage/`)

### Schema migrations — not started
- `MIGRATIONS: dict[str, callable]` in `schema.py`: `{"1→2": migrate_v1_to_v2}`
- On load: detect `_schema_version`, apply migration chain, return current model
- Old files never auto-updated (migration is an explicit CLI command)

### File locking — not started
- `filelock` (already in dependencies) wrapping `YAMLRunStore.save` and `sync_node_states`
- Needed for parallel test runs writing to the same YAML file

### `PostgresRunStore` — not started
- Implements `RunStoreBase` against a PostgreSQL database
- `RunGraph` → two tables: `run_graphs` + `run_nodes` + `run_paths` + `run_edges`
- Same 4-method interface; no changes required in `viz/` or `run_example.py`

### `SQLiteRunStore` — not started
- Lightweight alternative to PostgreSQL for single-user / CI scenarios

### Run indexing and filtering — not started
- `list_test_cases(tag=None, outcome=None, since=None)` — filtered queries
- Needed by the CLI `ai-repro list` command

---

## Capture Layer (`capture/`) — all not started

### `capture/otel_exporter.py`
- `RunSpanExporter(SpanExporter)` — converts completed OTel spans to `RunNode` objects
- Span attribute conventions: `ai.type`, `ai.model`, `ai.input_tokens`, `ai.messages_hash`, `ai.tool_name`, etc.
- Adds nodes to the active `RunGraph` via the context in `capture/context.py`

### `capture/context.py`
- `RunCapture` context manager: `with RunCapture(test_case_id=..., store=...) as run:`
- Registers `RunSpanExporter` with the OTel `TracerProvider`
- On exit: calls `force_flush()`, finalizes graph, calls `store.save()`
- Async variant: `async with RunCapture(...) as run:`

### `capture/claude_code_hooks.py`
- Translates Claude Code hook payloads (stdin JSON on `PostToolUse` / `Stop` events) into OTel spans
- `hooks/capture_hook.py` — the shell-invoked script called by `.claude/settings.json` hooks

### `capture/langchain_callback.py`
- `ReproducibilityCallbackHandler(BaseCallbackHandler)`
- Implements `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`
- Each callback emits an OTel span with `ai.*` attributes

### `capture/checkpoint.py`
- `@checkpoint(label="stage-2")` decorator — emits a `CHECKPOINT` node into the active run
- `CheckpointState`: serialized args/kwargs for resumable replay

### `messages_hash` computation — not started
- SHA-256 of `json.dumps(messages, sort_keys=True)`, truncated to 16 hex chars
- Required before `RunNode.metadata["messages_hash"]` can be populated automatically

---

## Analysis Layer (`analysis/`) — all not started

### `analysis/compare.py`
- `compare_paths(path_a: RunPath, path_b: RunPath) -> PathDiff`
- `PathDiff`: first divergence index, divergence type (different tool, different model response, extra step, missing step)

### `analysis/stats.py`
- `run_stats(graphs: list[RunGraph]) -> RunStats`
- `RunStats`: mean/p50/p95/p99 for token counts, latency, cost; success rate; path frequency table

### `analysis/patterns.py`
- `find_common_paths(graphs) -> list[tuple[list[str], int]]`
- `find_divergence_nodes(overlay_graph) -> list[RunNode]`

---

## Visualization (`viz/`) — partially missing

### `viz/terminal.py` — not started
- `show_run(graph: RunGraph)` — `rich` tree of a single run
- `show_overlay(graph: RunGraph)` — overlay with edge frequency labels

### `viz/mermaid.py` — not started
- `to_mermaid(graph: RunGraph) -> str`
- Overlay-aware: `-->|3/5 runs|` annotations on edges

---

## CLI (`cli.py`) — not started

Full Click CLI planned in `PLAN.md`:
```
ai-repro list [--tag]
ai-repro show <test-case-id> [--run] [--format terminal|mermaid]
ai-repro compare <test-case-id> <path-a> <path-b>
ai-repro overlay <test-case-id> [--export html|mermaid]
ai-repro export <test-case-id> --format mermaid|html|json
ai-repro replay <test-case-id> <path-id> [--from <node-id>]
ai-repro stats <test-case-id>
ai-repro tag <test-case-id> <path-id> <tag>
```

---

## Replay (`replay.py`) — not started

- `replay(test_case_id, path_id, from_node_id=None)` — re-run from a checkpoint with live LLM calls
- Restored execution saved as a new path with `parent_path_id` and `resumed_from_node` fields
- Depends on `capture/checkpoint.py` and `capture/context.py`

---

## Cost Computation — not started

- `RunCaptureConfig.cost_per_1k_tokens: dict[str, tuple[float, float]]` — model → (input_cost, output_cost)
- Auto-populate `RunNode.metadata["cost_usd"]` during capture
- Aggregate in `RunPath.metadata["total_cost_usd"]` and `RunGraph`-level summary