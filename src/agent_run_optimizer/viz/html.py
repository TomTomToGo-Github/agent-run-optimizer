from __future__ import annotations

import json

from agent_run_optimizer.graph.models import NodeType, RunGraph

_PATH_COLORS = ["#E63946", "#457B9D", "#2A9D8F", "#E9C46A", "#F4A261", "#9B72CF", "#264653"]

_TYPE_COLORS = {
    NodeType.LLM: "#5B8CDE",
    NodeType.TOOL: "#52B788",
    NodeType.HUMAN: "#F4A261",
    NodeType.CHECKPOINT: "#9B72CF",
}

_TYPE_SHAPES = {
    NodeType.LLM: "roundrectangle",
    NodeType.TOOL: "diamond",
    NodeType.HUMAN: "rectangle",
    NodeType.CHECKPOINT: "ellipse",
}

# Uses __PLACEHOLDER__ substitution to avoid conflict with Python .format() and JS braces.
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { overflow: auto; }   /* scrollbars appear here when window is too small */
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #f0f4f8;
      color: #1a202c;
      height: 100vh;
      min-width: 700px;
      min-height: 480px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* ── Header ───────────────────────────────────────────────────── */
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #1e293b;
      color: #f1f5f9;
      padding: 12px 20px;
      flex-shrink: 0;
      gap: 16px;
    }
    header h1 { font-size: 17px; font-weight: 600; white-space: nowrap; }
    .header-meta { font-size: 12px; color: #94a3b8; margin-top: 2px; max-width: 600px; }
    .controls { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

    #sync-btn {
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 7px 15px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    #sync-btn:hover { background: #2563eb; }
    #sync-status { font-size: 12px; color: #86efac; }

    /* ── Main layout ──────────────────────────────────────────────── */
    main { display: flex; flex: 1; overflow: hidden; }

    /* ── Sidebar ──────────────────────────────────────────────────── */
    #sidebar {
      width: 240px;
      flex-shrink: 0;
      background: #1e293b;
      color: #e2e8f0;
      overflow-y: auto;
      padding: 14px 12px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }
    .sidebar-section-title {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #64748b;
      margin-bottom: 8px;
      font-weight: 600;
    }

    /* ── Path items ───────────────────────────────────────────────── */
    .path-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 8px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 15px;
      transition: background 0.1s;
      user-select: none;
    }
    .path-item:hover { background: rgba(255,255,255,0.07); }
    .path-item.locked { background: rgba(255,255,255,0.11); }
    .path-dot { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; }
    .path-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .path-outcome {
      font-size: 13px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      flex-shrink: 0;
    }
    .outcome-success  { background: #14532d; color: #86efac; }
    .outcome-failure  { background: #7f1d1d; color: #fca5a5; }
    .outcome-partial  { background: #713f12; color: #fde68a; }
    .outcome-unknown  { background: #334155; color: #94a3b8; }

    /* ── Legend ───────────────────────────────────────────────────── */
    .legend { display: flex; flex-direction: column; gap: 8px; }
    .legend-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
    .lc { width: 14px; height: 10px; border-radius: 3px; flex-shrink: 0; }
    .lc-diamond {
      width: 10px; height: 10px;
      background: #52B788;
      transform: rotate(45deg);
      border-radius: 1px;
      flex-shrink: 0;
    }
    .lc-circle { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .lb-gold  { width: 14px; height: 10px; border: 2px solid #FFD700; border-radius: 3px; flex-shrink: 0; }
    .lb-pink  { width: 14px; height: 10px; border: 2px dashed #FF4081; border-radius: 3px; flex-shrink: 0; }

    .tip { font-size: 10px; color: #475569; margin-top: 4px; line-height: 1.4; }

    /* ── Graph canvas ─────────────────────────────────────────────── */
    #cy-wrap { flex: 1; position: relative; overflow: hidden; }
    #cy { width: 100%; height: 100%; }
    #lane-svg {
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      pointer-events: none;
    }

    /* ── Detail panel ─────────────────────────────────────────────── */
    #detail {
      width: 240px;
      flex-shrink: 0;
      background: #fff;
      border-left: 1px solid #e2e8f0;
      overflow-y: auto;
      padding: 14px;
      display: none;
    }
    #detail.open { display: block; }
    .detail-title { font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 3px; }
    .detail-type  { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin-bottom: 10px; }
    .detail-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
    .dbadge { font-size: 10px; padding: 2px 7px; border-radius: 9999px; font-weight: 600; }
    .dbadge-fixpoint  { background: #713f12; color: #fde68a; border: 1px solid #ca8a04; }
    .dbadge-important { background: #831843; color: #fbcfe8; }
    .detail-meta { font-size: 11px; }
    .detail-meta dt { color: #64748b; margin-top: 7px; }
    .detail-meta dd { color: #1e293b; word-break: break-all; }
    .detail-hint { font-size: 10px; color: #94a3b8; margin-top: 12px; }

    /* ── Toast ────────────────────────────────────────────────────── */
    #toast {
      position: fixed;
      bottom: 20px; right: 20px;
      padding: 9px 15px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      z-index: 9999;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s;
    }
    #toast.show { opacity: 1; }
    #toast.success { background: #14532d; color: #86efac; }
    #toast.error   { background: #7f1d1d; color: #fca5a5; }
  </style>
</head>
<body>

<header>
  <div>
    <h1>Run Graph &mdash; __TEST_CASE_ID__</h1>
    <div class="header-meta">__DESCRIPTION__</div>
  </div>
  <div class="controls">
    <span id="sync-status"></span>
    <button id="sync-btn">&#x21BB; Sync to Store</button>
  </div>
</header>

<main>
  <aside id="sidebar">
    <div>
      <div class="sidebar-section-title">Paths</div>
      <div id="path-list"></div>
      <p class="tip">Hover to highlight &nbsp;&middot;&nbsp; Click to lock</p>
    </div>
    <div>
      <div class="sidebar-section-title">Legend</div>
      <div class="legend">
        <div class="legend-row"><span class="lc" style="background:#5B8CDE;border-radius:3px"></span> LLM</div>
        <div class="legend-row"><span class="lc-diamond"></span> Tool</div>
        <div class="legend-row"><span class="lc" style="background:#F4A261"></span> Human</div>
        <div class="legend-row"><span class="lc-circle" style="background:#9B72CF"></span> Checkpoint</div>
        <div class="legend-row"><span class="lb-gold"></span> Required step</div>
        <div class="legend-row"><span class="lb-pink"></span> User-marked</div>
      </div>
      <p class="tip">Click node: required step &nbsp;&middot;&nbsp; Right-click: important</p>
    </div>
  </aside>

  <div id="cy-wrap">
    <div id="cy"></div>
    <svg id="lane-svg"></svg>
  </div>

  <div id="detail">
    <div class="detail-title" id="d-label"></div>
    <div class="detail-type"  id="d-type"></div>
    <div class="detail-badges" id="d-badges"></div>
    <dl class="detail-meta" id="d-meta"></dl>
    <p class="detail-hint">Click: required step &nbsp;&middot;&nbsp; Right-click: important</p>
  </div>
</main>

<div id="toast"></div>

<script>
/* ── Injected data ────────────────────────────────────────────────── */
const TEST_CASE_ID = __TEST_CASE_ID_JSON__;
const ELEMENTS     = __ELEMENTS_JSON__;
const PATHS        = __PATHS_JSON__;

/* ── Lane layout constants ────────────────────────────────────────── */
const LANE_W  = 210;   // horizontal distance between lane centres (model units)
const LEVEL_H = 95;    // vertical distance per depth level (model units)

/* ── Canonical ID → list of Cytoscape element IDs ─────────────────── */
// Deviating nodes are duplicated per path; this map lets hover/click
// find all copies of the same logical node.
const canonicalToElements = {};
ELEMENTS.filter(e => !e.data.source).forEach(e => {
    const cid = e.data.canonical_id;
    if (!canonicalToElements[cid]) canonicalToElements[cid] = [];
    canonicalToElements[cid].push(e.data.id);
});

/* ── Lane assignment ──────────────────────────────────────────────── */
// path_id null  → center lane (shared / fixpoint nodes)
// path_id set   → the named path's lane (deviating nodes)

// Paths alternate left / right of centre so the layout stays balanced.
// e.g. 3 paths: path-0 → -LANE_W, path-1 → +LANE_W, path-2 → -2*LANE_W
const laneX = { center: 0 };
PATHS.forEach((p, i) => {
    const sign  = (i % 2 === 0) ? -1 : 1;
    const steps = Math.floor(i / 2) + 1;
    laneX[p.id] = sign * steps * LANE_W;
});

/* ── Critical-path depths (longest path from root) ───────────────── */
function computeDepths() {
    const nodes = ELEMENTS.filter(e => !e.data.source).map(e => e.data.id);
    const edges  = ELEMENTS.filter(e =>  e.data.source);
    const adj = {}, inDeg = {};
    nodes.forEach(n => { adj[n] = []; inDeg[n] = 0; });
    edges.forEach(e => {
        if (adj[e.data.source]) {
            adj[e.data.source].push(e.data.target);
            inDeg[e.data.target] = (inDeg[e.data.target] || 0) + 1;
        }
    });
    const d = {};
    nodes.forEach(n => d[n] = 0);
    const q = nodes.filter(n => inDeg[n] === 0);
    while (q.length) {
        const n = q.shift();
        (adj[n] || []).forEach(c => {
            d[c] = Math.max(d[c], d[n] + 1);
            if (--inDeg[c] === 0) q.push(c);
        });
    }
    return d;
}
const depth = computeDepths();

/* ── Node positions ───────────────────────────────────────────────── */
const nodePos = {};
ELEMENTS.filter(e => !e.data.source).forEach(e => {
    nodePos[e.data.id] = {
        x: laneX[e.data.path_id || 'center'] ?? 0,
        y: depth[e.data.id] * LEVEL_H,
    };
});

/* ── Cytoscape init ───────────────────────────────────────────────── */
const cy = cytoscape({
    container: document.getElementById('cy'),
    elements:  ELEMENTS,
    style: [
        {
            selector: 'node',
            style: {
                'label':            'data(label)',
                'background-color': 'data(color)',
                'color':            '#1a202c',
                'text-valign':      'center',
                'text-halign':      'center',
                'font-size':        '13px',
                'font-family':      'system-ui, sans-serif',
                'font-weight':      '600',
                'width':            130,
                'height':           58,
                'shape':            'data(shape)',
                'border-width':     0,
            }
        },
        {
            selector: 'node[?is_fixpoint]',
            style: {
                'border-width': 3,
                'border-color': '#FFD700',
                'border-style': 'solid',
            }
        },
        {
            selector: 'node[?user_important]',
            style: {
                'overlay-color':   '#FF4081',
                'overlay-opacity': 0.22,
                'overlay-padding': 7,
                'border-width':    3,
                'border-color':    '#FF4081',
                'border-style':    'dashed',
            }
        },
        {
            selector: 'node[?is_fixpoint][?user_important]',
            style: { 'border-width': 3, 'border-color': '#FFD700' }
        },
        {
            selector: '.peer-hover',
            style: {
                'overlay-color':   '#ffffff',
                'overlay-opacity': 0.25,
                'overlay-padding': 5,
            }
        },
        {
            selector: 'edge',
            style: {
                'width':              2,
                'line-color':         '#94a3b8',
                'target-arrow-color': '#94a3b8',
                'target-arrow-shape': 'triangle',
                'curve-style':        'bezier',
            }
        },
        {
            selector: '.dimmed',
            style: { 'opacity': 0.1 }
        },
        {
            selector: 'node[?is_fixpoint].dimmed',
            style: { 'opacity': 0.45 }
        },
    ],
    layout: {
        name:     'preset',
        positions: nodePos,
        fit:      true,
        padding:  70,
    }
});

/* ── Lane divider overlay ─────────────────────────────────────────── */
const laneSvg = document.getElementById('lane-svg');
const cyWrap  = document.getElementById('cy-wrap');

// Sorted lanes by x-position for boundary computation
const sortedLanes = Object.entries(laneX).sort(([, a], [, b]) => a - b);

// Midpoints between adjacent lanes (model space) → become the divider lines
const dividers = [];
for (let i = 0; i < sortedLanes.length - 1; i++) {
    dividers.push((sortedLanes[i][1] + sortedLanes[i + 1][1]) / 2);
}

function mxToSx(mx) { return mx * cy.zoom() + cy.pan().x; }

function drawLanes() {
    const W = cyWrap.clientWidth;
    const H = cyWrap.clientHeight;
    laneSvg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    // Screen-space boundaries for background tints
    const screenDiv = [-Infinity, ...dividers.map(mxToSx), Infinity];

    let out = '';

    // Per-lane background tint
    sortedLanes.forEach(([laneId], i) => {
        if (laneId === 'center') return;
        const path = PATHS.find(p => p.id === laneId);
        if (!path) return;
        const x1 = Math.max(0, screenDiv[i]);
        const x2 = Math.min(W, screenDiv[i + 1]);
        if (x2 <= x1) return;
        out += `<rect x="${x1.toFixed(1)}" y="0" width="${(x2 - x1).toFixed(1)}" height="${H}"
                      fill="${path.color}" fill-opacity="0.06"/>`;
    });

    // Dashed divider lines
    dividers.forEach(mx => {
        const sx = mxToSx(mx);
        if (sx <= 0 || sx >= W) return;
        out += `<line x1="${sx.toFixed(1)}" y1="0" x2="${sx.toFixed(1)}" y2="${H}"
                      stroke="#64748b" stroke-width="1" stroke-dasharray="5 4" opacity="0.45"/>`;
    });

    // Lane labels fixed near the top of the viewport
    sortedLanes.forEach(([laneId, mx]) => {
        const sx = mxToSx(mx);
        if (sx < 30 || sx > W - 30) return;
        const isCenter = laneId === 'center';
        const label = isCenter ? '— required steps —' : laneId;
        const color = isCenter ? '#94a3b8' : (PATHS.find(p => p.id === laneId)?.color || '#94a3b8');
        out += `<text x="${sx.toFixed(1)}" y="22" text-anchor="middle"
                      fill="${color}" font-size="14" font-family="system-ui,sans-serif"
                      font-weight="600" opacity="0.85" letter-spacing="0.04em">${label}</text>`;
    });

    laneSvg.innerHTML = out;
}

cy.on('render', drawLanes);
window.addEventListener('resize', drawLanes);

/* ── Path list ────────────────────────────────────────────────────── */
const pathList = document.getElementById('path-list');
let lockedPath = null;

PATHS.forEach(path => {
    const item = document.createElement('div');
    item.className = 'path-item';
    item.innerHTML = `
        <span class="path-dot" style="background:${path.color}"></span>
        <span class="path-label">${path.id}</span>
        <span class="path-outcome outcome-${path.outcome}">${path.outcome}</span>
    `;

    item.addEventListener('mouseenter', () => { if (!lockedPath) highlightPath(path); });
    item.addEventListener('mouseleave', () => { if (!lockedPath) clearHighlight(); });
    item.addEventListener('click', () => {
        if (lockedPath === path.id) {
            lockedPath = null;
            item.classList.remove('locked');
            clearHighlight();
        } else {
            document.querySelectorAll('.path-item').forEach(el => el.classList.remove('locked'));
            lockedPath = path.id;
            item.classList.add('locked');
            highlightPath(path);
        }
    });

    pathList.appendChild(item);
});

/* ── Path highlighting ────────────────────────────────────────────── */
function highlightPath(path) {
    cy.edges().removeStyle('line-color').removeStyle('target-arrow-color').removeStyle('width');
    cy.elements().addClass('dimmed');

    new Set(path.nodes).forEach(id  => cy.$id(id).removeClass('dimmed'));
    new Set(path.edges).forEach(id  => {
        const e = cy.$id(id);
        e.removeClass('dimmed');
        e.style('line-color',         path.color);
        e.style('target-arrow-color', path.color);
        e.style('width',              3);
    });
}

function clearHighlight() {
    cy.elements().removeClass('dimmed');
    cy.edges().removeStyle('line-color').removeStyle('target-arrow-color').removeStyle('width');
}

/* ── Node interactions ────────────────────────────────────────────── */
const detail  = document.getElementById('detail');
const dLabel  = document.getElementById('d-label');
const dType   = document.getElementById('d-type');
const dBadges = document.getElementById('d-badges');
const dMeta   = document.getElementById('d-meta');

// Highlight all copies of the same logical node on hover
cy.on('mouseover', 'node', e => {
    const cid = e.target.data('canonical_id');
    (canonicalToElements[cid] || []).forEach(id => cy.$id(id).addClass('peer-hover'));
});
cy.on('mouseout', 'node', e => {
    const cid = e.target.data('canonical_id');
    (canonicalToElements[cid] || []).forEach(id => cy.$id(id).removeClass('peer-hover'));
});

// Left-click: toggle required step (is_fixpoint) on all copies
cy.on('tap', 'node', e => {
    const node   = e.target;
    const cid    = node.data('canonical_id');
    const newVal = !node.data('is_fixpoint');
    (canonicalToElements[cid] || []).forEach(id => cy.$id(id).data('is_fixpoint', newVal));
    cy.style().update();
    renderDetail(node);
});

// Right-click: toggle important (user_important) on all copies
cy.on('cxttap', 'node', e => {
    const node   = e.target;
    const cid    = node.data('canonical_id');
    const newVal = !node.data('user_important');
    (canonicalToElements[cid] || []).forEach(id => cy.$id(id).data('user_important', newVal));
    cy.style().update();
    renderDetail(node);
});

document.getElementById('cy').addEventListener('contextmenu', e => e.preventDefault());

cy.on('tap', e => { if (e.target === cy) detail.classList.remove('open'); });

function renderDetail(node) {
    const d = node.data();
    detail.classList.add('open');
    dLabel.textContent = d.label;
    dType.textContent  = d.type;
    dBadges.innerHTML = [
        d.is_fixpoint    ? '<span class="dbadge dbadge-fixpoint">Required step</span>' : '',
        d.user_important ? '<span class="dbadge dbadge-important">Important</span>'    : '',
    ].join('');
    dMeta.innerHTML = `<dt>ID</dt><dd>${d.canonical_id}</dd>` +
        Object.entries(d.metadata || {})
            .map(([k, v]) => `<dt>${k}</dt><dd>${typeof v === 'object' ? JSON.stringify(v) : v}</dd>`)
            .join('');
}

/* ── Sync ─────────────────────────────────────────────────────────── */
document.getElementById('sync-btn').addEventListener('click', async () => {
    const updates = {};
    const seen    = new Set();
    cy.nodes().forEach(n => {
        const cid = n.data('canonical_id');
        if (!seen.has(cid)) {
            seen.add(cid);
            updates[cid] = {
                user_important: !!n.data('user_important'),
                is_fixpoint:    !!n.data('is_fixpoint'),
            };
        }
    });
    document.getElementById('sync-status').textContent = 'Syncing…';
    try {
        const res  = await fetch('/api/sync', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ test_case_id: TEST_CASE_ID, updates }),
        });
        const json = await res.json();
        document.getElementById('sync-status').textContent = '';
        showToast(json.message, 'success');
    } catch (err) {
        document.getElementById('sync-status').textContent = '';
        showToast('Sync failed: ' + err.message, 'error');
    }
});

/* ── Toast ────────────────────────────────────────────────────────── */
function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `show ${type}`;
    setTimeout(() => { t.className = ''; }, 3000);
}
</script>
</body>
</html>
"""


class HtmlViz:
    def generate_html(self, graph: RunGraph) -> str:
        node_cy_map = self._compute_node_cy_map(graph)
        elements    = self._build_elements(graph, node_cy_map)
        paths_data  = self._build_paths_data(graph, node_cy_map)

        html = _HTML_TEMPLATE
        html = html.replace("__TITLE__",             f"Run Graph — {graph.test_case_id}")
        html = html.replace("__TEST_CASE_ID__",      graph.test_case_id)
        html = html.replace("__DESCRIPTION__",       graph.description or "")
        html = html.replace("__TEST_CASE_ID_JSON__", json.dumps(graph.test_case_id))
        html = html.replace("__ELEMENTS_JSON__",     json.dumps(elements))
        html = html.replace("__PATHS_JSON__",        json.dumps(paths_data))
        return html

    def _compute_node_cy_map(self, graph: RunGraph) -> dict[str, dict]:
        """Maps node_id → {path_id → cy_id} for deviating nodes, {None → node_id} for shared."""
        node_paths: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
        for path in graph.paths:
            for nid in path.node_sequence:
                if nid in node_paths:
                    node_paths[nid].append(path.path_id)

        num_paths = len(graph.paths)
        result: dict[str, dict] = {}

        for node_id, node in graph.nodes.items():
            paths = node_paths.get(node_id, [])
            shared = node.is_fixpoint or len(paths) == 0 or len(paths) >= num_paths
            if shared:
                result[node_id] = {None: node_id}
            else:
                result[node_id] = {
                    path.path_id: f"{node_id}__{path.path_id}"
                    for path in graph.paths
                    if node_id in path.node_sequence
                }

        return result

    def _build_elements(self, graph: RunGraph, node_cy_map: dict[str, dict]) -> list[dict]:
        elements: list[dict] = []

        for node_id, node in graph.nodes.items():
            base = {
                "label":          node.label,
                "type":           node.type.value,
                "is_fixpoint":    node.is_fixpoint,
                "user_important": node.user_important,
                "color":          _TYPE_COLORS.get(node.type, "#888"),
                "shape":          _TYPE_SHAPES.get(node.type, "ellipse"),
                "metadata":       node.metadata,
                "canonical_id":   node_id,
            }
            for path_id, cy_id in node_cy_map[node_id].items():
                elements.append({"data": {"id": cy_id, "path_id": path_id, **base}})

        seen: set[str] = set()
        for path in graph.paths:
            for edge in path.edges:
                src_map = node_cy_map.get(edge.source, {})
                tgt_map = node_cy_map.get(edge.target, {})
                src_cy  = src_map.get(path.path_id) or src_map.get(None) or edge.source
                tgt_cy  = tgt_map.get(path.path_id) or tgt_map.get(None) or edge.target
                eid = f"{src_cy}__{tgt_cy}"
                if eid not in seen:
                    seen.add(eid)
                    elements.append({
                        "data": {"id": eid, "source": src_cy, "target": tgt_cy, "paths": [path.path_id]},
                    })

        return elements

    def _build_paths_data(self, graph: RunGraph, node_cy_map: dict[str, dict]) -> list[dict]:
        result = []
        for i, path in enumerate(graph.paths):
            cy_nodes = []
            for nid in path.node_sequence:
                cy_map = node_cy_map.get(nid, {})
                cy_nodes.append(cy_map.get(path.path_id) or cy_map.get(None) or nid)

            cy_edges = []
            for edge in path.edges:
                src_map = node_cy_map.get(edge.source, {})
                tgt_map = node_cy_map.get(edge.target, {})
                src_cy  = src_map.get(path.path_id) or src_map.get(None) or edge.source
                tgt_cy  = tgt_map.get(path.path_id) or tgt_map.get(None) or edge.target
                cy_edges.append(f"{src_cy}__{tgt_cy}")

            result.append({
                "id":          path.path_id,
                "outcome":     path.outcome,
                "color":       _PATH_COLORS[i % len(_PATH_COLORS)],
                "nodes":       cy_nodes,
                "edges":       cy_edges,
                "duration_ms": path.duration_ms,
            })
        return result