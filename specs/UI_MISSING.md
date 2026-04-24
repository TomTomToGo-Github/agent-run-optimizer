# UI — Missing / Planned Features

Items are loosely ordered by priority. None are started; stub code does not exist.

---

## High Priority

### Overlay / Frequency Visualization
- Edge thickness proportional to number of runs that traversed it
- Node background intensity proportional to visit frequency
- Tooltip showing "N of M runs passed through this node"
- Required before the UI is useful for real multi-run analysis

### Graph Stats Panel
- Per-path summary: total duration, input/output token counts, estimated cost
- Per-node aggregate stats pulled from `RunNode.metadata`
- Visible without opening the detail panel (e.g. on hover tooltip or bottom bar)

### Zoom / Pan Controls
- On-screen `+` / `-` / `fit` buttons (Cytoscape scroll zoom works but is not obvious to new users)
- "Fit all" resets to show the entire graph
- Keyboard shortcuts: `f` = fit, `+`/`-` = zoom

### Node Filtering
- Toggle visibility by node type (hide all tool nodes, show only LLM nodes, etc.)
- Filter to "nodes on any failed path" / "nodes on all successful paths"
- Filter to fixpoints only

---

## Medium Priority

### Run Diff View
- Select two paths in the sidebar; UI highlights divergence point and exclusive nodes
- Colour-coded: shared (grey), path-A-only (left color), path-B-only (right color)
- Connects to the planned `analysis/compare.py` backend

### Edge Labels
- `RunEdge.label` and `RunEdge.type` rendered on edges (currently ignored by the UI)
- Toggle label visibility (clutters layout when graph is dense)

### Export from UI
- "Export PNG" button — Cytoscape `cy.png()` is a one-liner
- "Export Mermaid" button — calls the planned `viz/mermaid.py` backend via `/api/export`
- "Export JSON" button — returns raw graph data as a downloadable `.json`

### Node Search
- Search box in sidebar filters/highlights nodes by label substring
- Useful when a graph has many nodes

---

## Low Priority / Future

### Offline / CDN-Free Mode
- Bundle Cytoscape.js + dagre inline in the HTML (adds ~500 KB but removes the CDN dependency)
- Needed if running in an air-gapped environment

### Run Selector
- Dropdown in the header to switch between test cases without restarting the server
- Requires a `GET /api/graphs` endpoint returning `store.list_test_cases()`

### Timeline / Gantt View
- Horizontal bars showing each node's duration relative to the run start time
- Parallel vs sequential execution visible at a glance
- Requires `RunNode.metadata.latency_ms` and `RunPath.timestamp` to be populated

### Dark / Light Theme Toggle
- Current design: dark sidebar, light canvas
- A full dark-canvas mode would reduce eye strain for dense graphs

### Graph Minimap
- Small overview pane in a corner for large graphs with many nodes

### Persistent View State
- Remember zoom level and pan position across page reloads (localStorage)

### Multi-Test-Case Overlay
- Merge graphs from different test cases to find shared patterns across scenarios

### Annotation Layer
- Free-text notes attached to nodes, stored in `RunNode.metadata["annotations"]`
- Editable inline in the detail panel, synced to store on save