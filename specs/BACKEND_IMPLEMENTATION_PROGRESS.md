# Backend — Implementation Progress

All items below are fully implemented and tested as of 2026-04-23.

---

## Data Model (`graph/models.py`)

- [x] `NodeType` enum: `llm`, `tool`, `human`, `checkpoint`
- [x] `EdgeType` enum: `sequential`, `conditional`, `retry`, `parallel`
- [x] `RunNode` Pydantic model: `id`, `type`, `label`, `is_fixpoint`, `user_important`, `metadata`
- [x] `RunEdge` Pydantic model: `source`, `target`, `type`, `label`
- [x] `RunPath` Pydantic model: `path_id`, `outcome`, `timestamp`, `duration_ms`, `node_sequence`, `edges`, `metadata`
- [x] `RunGraph` Pydantic model: `test_case_id`, `description`, `created_at`, `tags`, `nodes` (shared pool), `paths`
- [x] All models use Pydantic v2 (`model_copy`, `Field(default_factory=...)`)

## Storage Abstraction (`storage/base.py`)

- [x] `RunStoreBase` abstract base class
- [x] Abstract methods: `load`, `save`, `sync_node_states`, `list_test_cases`
- [x] Docstring on `sync_node_states` explaining its role as the UI→store bridge

## YAML Serialization (`storage/schema.py`)

- [x] `graph_to_dict(graph: RunGraph) -> dict` — full graph to plain dict
- [x] `dict_to_graph(data: dict) -> RunGraph` — plain dict to `RunGraph`
- [x] `SCHEMA_VERSION = "1"` constant embedded in every saved file as `_schema_version`
- [x] Edge `from`/`to` keys in YAML ↔ `source`/`target` in Python model (translation handled in schema layer)
- [x] `datetime.fromisoformat` for all timestamp fields; `None`-safe
- [x] All enum values round-trip correctly (`.value` on write, `Enum(...)` on read)

## YAML Store (`storage/yaml_store.py`)

- [x] `YAMLRunStore(runs_dir)` — configurable directory, defaults to `"runs"`
- [x] `load(test_case_id)` — reads `{runs_dir}/{test_case_id}.yaml`
- [x] `save(graph)` — full overwrite with `yaml.dump` (`sort_keys=False` preserves author order)
- [x] `sync_node_states(test_case_id, updates)` — load → patch with `model_copy(update=...)` → save
- [x] `list_test_cases()` — glob `*.yaml`, return stems
- [x] UTF-8 encoding on all file I/O

## HTML Visualization (`viz/html.py`)

- [x] `HtmlViz.generate_html(graph) -> str` — stateless, side-effect-free
- [x] `_build_elements(graph)` — converts `RunGraph` to Cytoscape.js `elements` array (nodes + edges)
- [x] Edge deduplication: one element per unique `(source, target)` pair; `paths` list embedded in edge data
- [x] `_build_paths_data(graph)` — path color assignment, edge ID list, node ID list per path
- [x] All data injected via `__PLACEHOLDER__` string substitution (avoids Python `.format()` / JS brace conflicts)
- [x] Template uses CDN (unpkg): `cytoscape@3.28.1`, `dagre@0.8.5`, `cytoscape-dagre@2.5.0`

## Example Data (`runs/incident-resolution.yaml`)

- [x] 8 nodes: 3 LLM, 4 tool, 0 human, 0 checkpoint
- [x] 3 fixpoints: `llm-initial`, `llm-resolve`, `llm-verify`
- [x] 3 paths: `run-001` (success, reads logs), `run-002` (success, checks metrics), `run-003` (partial, deep analysis, no fix applied)
- [x] Graph topology: shared entry + branch + merge + shared exit
- [x] Schema version `"1"` present

## Entry Point (`run_example.py`)

- [x] `serve_and_open(test_case_id, store, port)` — full pipeline: load → generate HTML → start server → open browser
- [x] `_make_handler(html, store, test_case_id)` — closure-based HTTP handler factory; no global state
- [x] `GET /` → serves HTML (200); anything else → 404
- [x] `POST /api/sync` → parses JSON body → `store.sync_node_states()` → JSON response
- [x] `_find_free_port(start, attempts)` — scans 8765–8784 for an available port
- [x] Daemon thread for server; clean `Ctrl-C` shutdown via `server.shutdown()`
- [x] CLI via `argparse`: `--test-case`, `--runs-dir`, `--port`
- [x] Comment marking where to swap in a different `RunStoreBase` implementation