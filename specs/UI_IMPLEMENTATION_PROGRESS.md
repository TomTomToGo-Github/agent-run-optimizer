# UI — Implementation Progress

All items below are fully implemented and working as of 2026-04-23.

---

## Graph Rendering

- [x] **Cytoscape.js** integration (v3.28.1, loaded from unpkg CDN)
- [x] **dagre layout** (v0.8.5 + cytoscape-dagre v2.5.0) — left-to-right DAG layout
- [x] **Shared node pool** — nodes deduplicated across paths; one visual node per logical node
- [x] **Edge deduplication** — one visual edge per unique (source, target) pair, annotated with which paths use it

## Node Styling

- [x] Shape by `NodeType`: roundrectangle (LLM), diamond (tool), rectangle (human), ellipse (checkpoint)
- [x] Color by `NodeType`: blue, green, orange, purple
- [x] Gold solid border for `is_fixpoint: true`
- [x] Pink dashed border + pink overlay for `user_important: true`
- [x] Both fixpoint + important: gold border + pink overlay (combined)
- [x] Labels rendered below nodes

## Path Interactions

- [x] Sidebar path list with color dot + outcome badge per path
- [x] **Hover** path → highlights path nodes/edges, dims everything else (10% opacity)
- [x] **Fixpoints respect dimming floor**: minimum 45% opacity even when not in active path
- [x] **Click path** → locks highlight (prevents mouseleave from clearing)
- [x] **Click again** → unlocks
- [x] Active path edges rendered in path color with increased width (3 px)

## Node Click — Importance Toggle

- [x] Click any node → toggles `user_important` boolean on the node data object
- [x] Style updates immediately via `cy.style().update()`
- [x] Detail panel opens on right with: label, type, fixpoint/important badges, all `metadata` key-value pairs
- [x] Click canvas background → closes detail panel

## Sync

- [x] **Sync button** in header
- [x] Collects `{ nodeId: { user_important } }` for all nodes
- [x] `POST /api/sync` with JSON body `{ test_case_id, updates }`
- [x] Server-side calls `store.sync_node_states()` — backend-agnostic
- [x] Toast notification: green on success, red on error, auto-dismisses after 3 s
- [x] Sync-status label next to button shows "Syncing…" while request is in flight

## Layout

- [x] Full-viewport flex layout (header + main)
- [x] Sidebar (210 px) — paths + legend
- [x] Graph canvas (flex: 1) — fills remaining space
- [x] Detail panel (240 px) — hidden by default, opens on node click
- [x] Legend: color swatches + diamond shape indicator + border-style indicators

## Server (`run_example.py`)

- [x] `GET /` — serves generated HTML (inline, no separate static files)
- [x] `POST /api/sync` — delegates to `store.sync_node_states()`
- [x] Auto-selects free port (8765+)
- [x] Opens browser tab automatically (`webbrowser.open`)
- [x] Runs HTTP server in daemon thread; `Ctrl-C` shuts it down cleanly
- [x] Console startup message: test case ID, store class name, URL