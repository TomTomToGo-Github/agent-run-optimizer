# UI — Interactive Run Graph Visualization

## Overview

A browser-based interactive graph that shows all execution paths for a given test case overlaid on a single DAG. Powered by [Cytoscape.js](https://js.cytoscape.org/) with the `dagre` layout extension. Served locally by `run_example.py`.

---

## How to Start

```bash
# from the project root
python run_example.py
# or with arguments:
python run_example.py --test-case incident-resolution --runs-dir runs --port 8765
```

A browser tab opens automatically at `http://localhost:<port>`. Press `Ctrl-C` to stop.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Run Graph — <test-case-id>         [↻ Sync to Store]            │
│ <description>                                                    │
├────────────────┬─────────────────────────────────────────────────┤
│ PATHS          │                                                 │
│  ● run-001 ✓   │                                                 │
│  ● run-002 ✓   │         Cytoscape.js graph (DAG, LR layout)    │
│  ● run-003 ~   │                                                 │
│                │                                                 │
│ LEGEND         ├─────────────────────────────────────────────────┤
│  □ LLM         │  Node Detail Panel (opens on node click)        │
│  ◇ Tool        │  — label, type, fixpoint/important badges       │
│  □ Human       │  — all metadata key/value pairs                 │
│  ○ Checkpoint  │                                                 │
│  gold = fix    │                                                 │
│  pink = imp    │                                                 │
└────────────────┴─────────────────────────────────────────────────┘
```

---

## Interactions

### Path Highlighting (sidebar)
- **Hover** a path item → highlights all nodes and edges belonging to that path; everything else dims to 10% opacity
- **Click** a path item → locks the highlight; click again to unlock
- Fixpoint nodes never drop below 45% opacity — they remain legible regardless of which path is active

### Node Visual Encoding

| Attribute | Visual |
|---|---|
| `type: llm` | Rounded rectangle, blue (#5B8CDE) |
| `type: tool` | Diamond, green (#52B788) |
| `type: human` | Rectangle, orange (#F4A261) |
| `type: checkpoint` | Ellipse, purple (#9B72CF) |
| `is_fixpoint: true` | 3 px solid gold border |
| `user_important: true` | 3 px dashed pink border + pink overlay |
| Both fixpoint + important | Gold border + pink overlay |

### Node Click — Toggle Important
- Click any node to toggle `user_important` on/off
- The detail panel slides in on the right showing: label, type, fixpoint/important badges, and all metadata fields
- Click the canvas background to close the detail panel

### Sync Button
- Collects the current `user_important` state for every node
- Sends a `POST /api/sync` request with `{ test_case_id, updates: { nodeId: { user_important: bool } } }`
- The server calls `store.sync_node_states()` — writes changes back to whatever backend is configured (YAML today, any `RunStoreBase` tomorrow)
- A toast notification confirms success or reports errors

---

## Visual Design

- **Dark header + sidebar**, light graph canvas — optimised for graph readability
- **Path colors** (auto-assigned, up to 7 distinct): red, steel-blue, teal, gold, orange, purple, dark-teal
- **Outcome badges** in sidebar: green = success, red = failure, amber = partial, grey = unknown
- Cytoscape.js handles zoom (scroll wheel) and pan (drag canvas) natively