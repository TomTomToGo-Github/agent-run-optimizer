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
    html { overflow: auto; }
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
    /* ── Case selector + sync (live in sidebar) ──────────────────── */
    #case-select {
      width: 100%;
      background: #334155;
      color: #e2e8f0;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 7px 10px;
      font-size: 20px;
      cursor: pointer;
      margin-bottom: 8px;
    }
    #case-select:hover { background: #3b4f6b; }
    #case-select:focus { outline: none; }
    #case-select:disabled { opacity: 0.5; cursor: wait; }

    .sync-row { display: flex; align-items: center; gap: 8px; }
    #sync-btn {
      flex: 1;
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 7px 10px;
      font-size: 20px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    #sync-btn:hover { background: #2563eb; }
    #sync-status { font-size: 18px; color: #86efac; white-space: nowrap; }

    /* ── Main layout ──────────────────────────────────────────────── */
    main { display: flex; flex: 1; overflow: hidden; }

    /* ── Sidebar ──────────────────────────────────────────────────── */
    #sidebar {
      width: 480px;
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
      font-size: 18px;
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
      font-size: 22px;
      transition: background 0.1s;
      user-select: none;
    }
    .path-item:hover { background: rgba(255,255,255,0.07); }
    .path-item.locked { background: rgba(255,255,255,0.11); }
    .path-dot { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; }
    .path-label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .path-outcome {
      font-size: 20px;
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
    .legend-row { display: flex; align-items: center; gap: 8px; font-size: 20px; }
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

    .tip { font-size: 15px; color: #475569; margin-top: 4px; line-height: 1.4; }

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

    /* ── Cost overlay buttons ─────────────────────────────────────── */
    #cost-btn-container {
      position: absolute; top: 0; left: 0;
      width: 100%; height: 100%;
      pointer-events: none;
      z-index: 5;
    }
    .cost-btn {
      position: absolute;
      width: 20px; height: 20px;
      border-radius: 50%;
      background: #14532d;
      color: #86efac;
      border: 1px solid #166534;
      font-size: 11px;
      cursor: default;
      pointer-events: auto;
      padding: 0;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700;
      transition: background 0.12s;
      line-height: 1;
    }
    .cost-btn:hover { background: #166534; border-color: #86efac; }

    .path-cost-btn {
      background: rgba(253,230,138,0.12);
      color: #fde68a;
      border: 1px solid rgba(253,230,138,0.35);
      border-radius: 4px;
      padding: 1px 6px;
      font-size: 16px;
      cursor: pointer;
      flex-shrink: 0;
      font-weight: 700;
      transition: background 0.12s;
      line-height: 1.4;
    }
    .path-cost-btn:hover { background: rgba(253,230,138,0.25); }

    .path-toggle-btn {
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      padding: 0;
      flex-shrink: 0;
      line-height: 1;
      transition: color 0.15s, opacity 0.15s;
    }

    #path-controls { display: flex; gap: 6px; margin-bottom: 8px; }
    .path-all-btn {
      flex: 1;
      background: #334155;
      color: #94a3b8;
      border: 1px solid #475569;
      border-radius: 5px;
      padding: 5px 8px;
      font-size: 15px;
      cursor: pointer;
      transition: background 0.12s, color 0.12s;
    }
    .path-all-btn:hover { background: #3b4f6b; color: #e2e8f0; }

    /* ── Cost popup ─────────────────────────────────────────────────── */
    #cost-popup {
      position: fixed;
      z-index: 9998;
      background: #14532d;
      color: #d1fae5;
      border: 1px solid #166534;
      border-radius: 8px;
      padding: 10px 14px;
      min-width: 170px;
      max-width: 260px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.45);
      display: none;
      font-size: 13px;
      pointer-events: none;
    }
    #cost-popup.open { display: block; }
    .cost-popup-title {
      font-weight: 700; margin-bottom: 7px; font-size: 12px;
      color: #86efac; text-transform: uppercase; letter-spacing: 0.06em;
    }
    .cost-popup-row { display: flex; justify-content: space-between; gap: 14px; padding: 2px 0; }
    .cost-popup-key { color: #6ee7b7; white-space: nowrap; }
    .cost-popup-val { font-weight: 600; font-variant-numeric: tabular-nums; }
  </style>
</head>
<body>

<header>
  <div>
    <h1>Run Graph &mdash; <span id="case-title">__TEST_CASE_ID__</span></h1>
    <div class="header-meta" id="case-description">__DESCRIPTION__</div>
  </div>
</header>

<main>
  <aside id="sidebar">
    <div>
      <div class="sidebar-section-title">Agent Run</div>
      <select id="case-select"></select>
      <div class="sync-row">
        <button id="sync-btn">&#x21BB; Sync to Store</button>
        <span id="sync-status"></span>
      </div>
    </div>
    <div>
      <div class="sidebar-section-title">Paths</div>
      <div id="path-controls">
        <button id="disable-all-btn" class="path-all-btn">Disable all</button>
        <button id="enable-all-btn"  class="path-all-btn">Enable all</button>
      </div>
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
    <div id="cost-btn-container"></div>
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
<div id="cost-popup"></div>

<script>
/* ── Injected data ────────────────────────────────────────────────── */
const INITIAL_CASE_ID  = __TEST_CASE_ID_JSON__;
const INITIAL_ELEMENTS = __ELEMENTS_JSON__;
const INITIAL_PATHS    = __PATHS_JSON__;
const INITIAL_DESC     = __DESCRIPTION_JSON__;
const CASES            = __CASES_JSON__;

/* ── Constants ────────────────────────────────────────────────────── */
const LANE_W  = 210;
const LEVEL_H = 95;

/* ── Cytoscape style (static across graphs) ───────────────────────── */
const CY_STYLE = [
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
        style: { 'border-width': 3, 'border-color': '#FFD700', 'border-style': 'solid' }
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
        style: { 'overlay-color': '#ffffff', 'overlay-opacity': 0.25, 'overlay-padding': 5 }
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
    { selector: '.dimmed',                       style: { 'opacity': 0.1  } },
    { selector: 'node[?is_fixpoint].dimmed',     style: { 'opacity': 0.45 } },
];

/* ── Module-level state ───────────────────────────────────────────── */
let cy               = null;
let currentCaseId    = INITIAL_CASE_ID;
let currentDrawLanes = null;
let costBtnMap        = {};

/* ── Static DOM refs ──────────────────────────────────────────────── */
const detail  = document.getElementById('detail');
const dLabel  = document.getElementById('d-label');
const dType   = document.getElementById('d-type');
const dBadges = document.getElementById('d-badges');
const dMeta   = document.getElementById('d-meta');
const laneSvg = document.getElementById('lane-svg');
const cyWrap  = document.getElementById('cy-wrap');

/* ── Case dropdown ────────────────────────────────────────────────── */
const caseSelect = document.getElementById('case-select');
CASES.forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = id;
    opt.selected = (id === INITIAL_CASE_ID);
    caseSelect.appendChild(opt);
});
caseSelect.addEventListener('change', () => loadTestCase(caseSelect.value));

/* ── Load a test case from the server ────────────────────────────── */
async function loadTestCase(testCaseId) {
    caseSelect.disabled = true;
    try {
        const res = await fetch(`/api/graph?id=${encodeURIComponent(testCaseId)}`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        initGraph(data.elements, data.paths, data.test_case_id, data.description);
    } catch (err) {
        showToast('Load failed: ' + err.message, 'error');
        caseSelect.value = currentCaseId;
    } finally {
        caseSelect.disabled = false;
    }
}

/* ── Depth computation (pure) ─────────────────────────────────────── */
function computeDepths(elements) {
    const nodes = elements.filter(e => !e.data.source).map(e => e.data.id);
    const edges  = elements.filter(e =>  e.data.source);
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

/* ── Cost helpers ─────────────────────────────────────────────────── */
function formatMs(ms) {
    return ms >= 1000 ? (ms / 1000).toFixed(2) + 's' : Math.round(ms) + 'ms';
}
function formatUSD(usd) {
    return usd >= 0.01 ? '$' + usd.toFixed(4) : '$' + usd.toFixed(6);
}
function pathTotalCost(path) {
    const seen = new Set();
    const total = {};
    path.nodes.forEach(cyId => {
        if (seen.has(cyId)) return;
        seen.add(cyId);
        const cost = cy.$id(cyId).data('cost');
        if (!cost) return;
        ['latency_ms','cost_usd','input_tokens','output_tokens'].forEach(k => {
            if (cost[k] != null) total[k] = (total[k] || 0) + cost[k];
        });
    });
    return total;
}
function showCostPopup(title, cost, clientX, clientY) {
    const popup = document.getElementById('cost-popup');
    const FIELDS = [
        ['latency_ms',    'Latency',       v => formatMs(v)],
        ['cost_usd',      'Cost',          v => formatUSD(v)],
        ['input_tokens',  'Input tokens',  v => v.toLocaleString()],
        ['output_tokens', 'Output tokens', v => v.toLocaleString()],
    ];
    let html = `<div class="cost-popup-title">${title}</div>`;
    let hasAny = false;
    FIELDS.forEach(([k, label, fmt]) => {
        if (cost[k] != null) {
            html += `<div class="cost-popup-row"><span class="cost-popup-key">${label}</span><span class="cost-popup-val">${fmt(cost[k])}</span></div>`;
            hasAny = true;
        }
    });
    const totalTok = (cost.input_tokens || 0) + (cost.output_tokens || 0);
    if (cost.input_tokens != null || cost.output_tokens != null) {
        html += `<div class="cost-popup-row" style="border-top:1px solid rgba(110,231,183,0.25);margin-top:3px;padding-top:3px"><span class="cost-popup-key">Total tokens</span><span class="cost-popup-val">${totalTok.toLocaleString()}</span></div>`;
        hasAny = true;
    }
    if (!hasAny) html += '<div class="cost-popup-key">No cost data</div>';
    popup.innerHTML = html;
    popup.style.left = Math.min(clientX + 8, window.innerWidth - 280) + 'px';
    popup.style.top  = Math.max(8, Math.min(clientY - 20, window.innerHeight - 180)) + 'px';
    popup.classList.add('open');
}
function hideCostPopup() {
    document.getElementById('cost-popup').classList.remove('open');
}
function updateCostOverlays() {
    if (!cy) return;
    cy.nodes().forEach(node => {
        const btn = costBtnMap[node.data('id')];
        if (!btn) return;
        const pos = node.renderedPosition();
        const hw  = node.renderedWidth()  / 2;
        const hh  = node.renderedHeight() / 2;
        btn.style.left = (pos.x + hw - 12) + 'px';
        btn.style.top  = (pos.y - hh - 8)  + 'px';
    });
}

/* ── Core graph initialization ────────────────────────────────────── */
function initGraph(elements, paths, testCaseId, description) {
    currentCaseId = testCaseId;

    // Update header
    document.getElementById('case-title').textContent = testCaseId;
    document.getElementById('case-description').textContent = description || '';
    document.title = `Run Graph — ${testCaseId}`;

    // Reset UI state
    detail.classList.remove('open');
    document.getElementById('path-list').innerHTML = '';

    // Cleanup previous graph
    if (currentDrawLanes) window.removeEventListener('resize', currentDrawLanes);
    if (cy) { cy.destroy(); cy = null; }
    costBtnMap = {};
    document.getElementById('cost-btn-container').innerHTML = '';
    hideCostPopup();

    /* ── canonical_id → list of cy element IDs ── */
    const canonicalToElements = {};
    elements.filter(e => !e.data.source).forEach(e => {
        const cid = e.data.canonical_id;
        if (!canonicalToElements[cid]) canonicalToElements[cid] = [];
        canonicalToElements[cid].push(e.data.id);
    });

    /* ── Lane X positions ── */
    const laneX = { center: 0 };
    const leftCount = Math.floor(paths.length / 2);
    paths.forEach((p, i) => {
        laneX[p.id] = i < leftCount
            ? (i - leftCount) * LANE_W
            : (i - leftCount + 1) * LANE_W;
    });

    /* ── Node positions ── */
    const depth = computeDepths(elements);
    const nodePos = {};
    elements.filter(e => !e.data.source).forEach(e => {
        nodePos[e.data.id] = {
            x: laneX[e.data.path_id || 'center'] ?? 0,
            y: depth[e.data.id] * LEVEL_H,
        };
    });

    /* ── Cytoscape instance ── */
    cy = cytoscape({
        container: document.getElementById('cy'),
        elements,
        style:  CY_STYLE,
        layout: { name: 'preset', positions: nodePos, fit: true, padding: 70 },
    });

    /* ── Cost overlay buttons ── */
    cy.nodes().forEach(node => {
        const cost = node.data('cost');
        if (!cost) return;
        const btn = document.createElement('button');
        btn.className = 'cost-btn';
        btn.textContent = '$';
        btn.addEventListener('mousedown', ev => ev.stopPropagation());
        btn.addEventListener('mouseenter', ev => {
            const r = ev.currentTarget.getBoundingClientRect();
            showCostPopup(node.data('label'), cost, r.right, r.top + r.height / 2);
        });
        btn.addEventListener('mouseleave', hideCostPopup);
        document.getElementById('cost-btn-container').appendChild(btn);
        costBtnMap[node.data('id')] = btn;
    });

    /* ── Lane divider overlay ── */
    function mxToSx(mx) { return mx * cy.zoom() + cy.pan().x; }

    function drawLanes() {
        const W = cyWrap.clientWidth;
        const H = cyWrap.clientHeight;
        laneSvg.setAttribute('viewBox', `0 0 ${W} ${H}`);
        const sortedLanes = Object.entries(laneX).sort(([, a], [, b]) => a - b);
        const dividers = [];
        for (let i = 0; i < sortedLanes.length - 1; i++) {
            dividers.push((sortedLanes[i][1] + sortedLanes[i + 1][1]) / 2);
        }
        const screenDiv = [-Infinity, ...dividers.map(mxToSx), Infinity];
        let out = '';
        sortedLanes.forEach(([laneId], i) => {
            if (laneId === 'center') return;
            const path = paths.find(p => p.id === laneId);
            if (!path) return;
            const x1 = Math.max(0, screenDiv[i]);
            const x2 = Math.min(W, screenDiv[i + 1]);
            if (x2 <= x1) return;
            out += `<rect x="${x1.toFixed(1)}" y="0" width="${(x2 - x1).toFixed(1)}" height="${H}"
                          fill="${path.color}" fill-opacity="0.06"/>`;
        });
        dividers.forEach(mx => {
            const sx = mxToSx(mx);
            if (sx <= 0 || sx >= W) return;
            out += `<line x1="${sx.toFixed(1)}" y1="0" x2="${sx.toFixed(1)}" y2="${H}"
                          stroke="#64748b" stroke-width="1" stroke-dasharray="5 4" opacity="0.45"/>`;
        });
        sortedLanes.forEach(([laneId, mx]) => {
            const sx = mxToSx(mx);
            if (sx < 30 || sx > W - 30) return;
            const isCenter = laneId === 'center';
            const label = isCenter ? '— ideal path —' : laneId;
            const color = isCenter ? '#94a3b8' : (paths.find(p => p.id === laneId)?.color || '#94a3b8');
            out += `<text x="${sx.toFixed(1)}" y="24" text-anchor="middle"
                          fill="${color}" font-size="16" font-family="system-ui,sans-serif"
                          font-weight="700" opacity="1" letter-spacing="0.06em">${label}</text>`;
        });
        laneSvg.innerHTML = out;
        updateCostOverlays();
    }

    currentDrawLanes = drawLanes;
    cy.on('render', drawLanes);
    window.addEventListener('resize', drawLanes);

    /* ── Path visibility ── */
    let hiddenPaths = new Set();
    const elemById = {};
    elements.forEach(e => { if (e.data && e.data.id) elemById[e.data.id] = e.data; });
    const sharedNodePaths = {};
    paths.forEach(path => {
        path.nodes.forEach(cyId => {
            const ed = elemById[cyId];
            if (ed && ed.path_id === null) {
                if (!sharedNodePaths[ed.canonical_id]) sharedNodePaths[ed.canonical_id] = [];
                if (!sharedNodePaths[ed.canonical_id].includes(path.id))
                    sharedNodePaths[ed.canonical_id].push(path.id);
            }
        });
    });
    function updatePathVisibility() {
        cy.nodes().forEach(node => {
            const pathId = node.data('path_id');
            let hide;
            if (pathId !== null) {
                hide = hiddenPaths.has(pathId);
            } else {
                const cid = node.data('canonical_id');
                const nodePaths = sharedNodePaths[cid] || [];
                hide = nodePaths.length > 0 && nodePaths.every(p => hiddenPaths.has(p));
            }
            node.style('display', hide ? 'none' : 'element');
            const btn = costBtnMap[node.data('id')];
            if (btn) btn.style.display = hide ? 'none' : '';
        });
        cy.edges().forEach(edge => {
            const edgePaths = edge.data('paths') || [];
            const hide = edgePaths.length > 0 && edgePaths.every(p => hiddenPaths.has(p));
            edge.style('display', hide ? 'none' : 'element');
        });
    }
    function relayout() {
        const visiblePaths = paths.filter(p => !hiddenPaths.has(p.id));
        const newLeftCount = Math.floor(visiblePaths.length / 2);
        Object.keys(laneX).forEach(k => { if (k !== 'center') delete laneX[k]; });
        visiblePaths.forEach((p, i) => {
            laneX[p.id] = i < newLeftCount
                ? (i - newLeftCount) * LANE_W
                : (i - newLeftCount + 1) * LANE_W;
        });
        cy.nodes().forEach(node => {
            if (node.style('display') === 'none') return;
            const pathId = node.data('path_id');
            const targetX = (node.data('is_fixpoint') || pathId === null)
                ? 0 : (laneX[pathId] ?? 0);
            node.animate({ position: { x: targetX, y: node.position('y') } }, { duration: 300 });
        });
        setTimeout(() => cy.fit(undefined, 70), 320);
        drawLanes();
    }
    function applyPathVisibility() {
        updatePathVisibility();
        relayout();
    }

    /* ── Path list ── */
    let lockedPath = null;
    const pathList = document.getElementById('path-list');
    const toggleBtnByPath = {};

    function highlightPath(path) {
        cy.edges().removeStyle('line-color').removeStyle('target-arrow-color').removeStyle('width');
        cy.elements().addClass('dimmed');
        new Set(path.nodes).forEach(id => cy.$id(id).removeClass('dimmed'));
        new Set(path.edges).forEach(id => {
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

    paths.forEach(path => {
        const item = document.createElement('div');
        item.className = 'path-item';
        item.innerHTML = `
            <span class="path-dot" style="background:${path.color}"></span>
            <span class="path-label">${path.id}</span>
            <span class="path-outcome outcome-${path.outcome}">${path.outcome}</span>
        `;
        const pathCostBtn = document.createElement('button');
        pathCostBtn.className = 'path-cost-btn';
        pathCostBtn.textContent = '$';
        pathCostBtn.addEventListener('mousedown', ev => ev.stopPropagation());
        pathCostBtn.addEventListener('mouseenter', ev => {
            const r = ev.currentTarget.getBoundingClientRect();
            showCostPopup(path.id + ' — total', pathTotalCost(path), r.right, r.top + r.height / 2);
        });
        pathCostBtn.addEventListener('mouseleave', hideCostPopup);
        item.appendChild(pathCostBtn);
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'path-toggle-btn';
        toggleBtn.textContent = '●';
        toggleBtn.style.color = path.color;
        toggleBtn.addEventListener('click', ev => {
            ev.stopPropagation();
            if (hiddenPaths.has(path.id)) {
                hiddenPaths.delete(path.id);
                toggleBtn.textContent = '●';
                toggleBtn.style.color = path.color;
                item.style.opacity = '1';
            } else {
                hiddenPaths.add(path.id);
                toggleBtn.textContent = '○';
                toggleBtn.style.color = '#64748b';
                item.style.opacity = '0.45';
            }
            applyPathVisibility();
        });
        toggleBtnByPath[path.id] = toggleBtn;
        item.insertBefore(toggleBtn, item.firstChild);
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

    document.getElementById('disable-all-btn').onclick = () => {
        paths.forEach(p => {
            hiddenPaths.add(p.id);
            const b = toggleBtnByPath[p.id];
            if (b) { b.textContent = '○'; b.style.color = '#64748b'; }
        });
        document.querySelectorAll('#path-list .path-item').forEach(el => el.style.opacity = '0.45');
        applyPathVisibility();
    };
    document.getElementById('enable-all-btn').onclick = () => {
        hiddenPaths.clear();
        paths.forEach(p => {
            const b = toggleBtnByPath[p.id];
            if (b) { b.textContent = '●'; b.style.color = p.color; }
        });
        document.querySelectorAll('#path-list .path-item').forEach(el => el.style.opacity = '1');
        applyPathVisibility();
    };

    /* ── Node interactions ── */
    cy.on('mouseover', 'node', e => {
        const cid = e.target.data('canonical_id');
        (canonicalToElements[cid] || []).forEach(id => cy.$id(id).addClass('peer-hover'));
    });
    cy.on('mouseout', 'node', e => {
        const cid = e.target.data('canonical_id');
        (canonicalToElements[cid] || []).forEach(id => cy.$id(id).removeClass('peer-hover'));
    });
    cy.on('tap', 'node', e => {
        const node   = e.target;
        const cid    = node.data('canonical_id');
        const newVal = !node.data('is_fixpoint');
        (canonicalToElements[cid] || []).forEach(id => {
            const n = cy.$id(id);
            n.data('is_fixpoint', newVal);
            const targetX = newVal ? 0 : (nodePos[id]?.x ?? n.position('x'));
            n.animate({ position: { x: targetX, y: n.position('y') } }, { duration: 280 });
        });
        cy.style().update();
        renderDetail(node);
    });
    cy.on('cxttap', 'node', e => {
        const node   = e.target;
        const cid    = node.data('canonical_id');
        const newVal = !node.data('user_important');
        (canonicalToElements[cid] || []).forEach(id => cy.$id(id).data('user_important', newVal));
        cy.style().update();
        renderDetail(node);
    });
    cy.on('tap', e => { if (e.target === cy) detail.classList.remove('open'); });
}

/* ── renderDetail ─────────────────────────────────────────────────── */
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

/* ── Prevent browser context menu on the graph ────────────────────── */
document.getElementById('cy').addEventListener('contextmenu', e => e.preventDefault());

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
            body:    JSON.stringify({ test_case_id: currentCaseId, updates }),
        });
        const json = await res.json();
        document.getElementById('sync-status').textContent = '';
        showToast(json.message, 'success');
        await refreshCases();
    } catch (err) {
        document.getElementById('sync-status').textContent = '';
        showToast('Sync failed: ' + err.message, 'error');
    }
});

/* ── Refresh dropdown from server ─────────────────────────────────── */
async function refreshCases() {
    try {
        const res   = await fetch('/api/cases');
        if (!res.ok) return;
        const data  = await res.json();
        const cases = data.cases || [];
        caseSelect.innerHTML = '';
        cases.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            opt.selected = (id === currentCaseId);
            caseSelect.appendChild(opt);
        });
    } catch (_) { /* best-effort — ignore network errors */ }
}

/* ── Toast ────────────────────────────────────────────────────────── */
function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `show ${type}`;
    setTimeout(() => { t.className = ''; }, 3000);
}

/* ── Initial render ───────────────────────────────────────────────── */
initGraph(INITIAL_ELEMENTS, INITIAL_PATHS, INITIAL_CASE_ID, INITIAL_DESC);
</script>
</body>
</html>
"""


class HtmlViz:
    def build_graph_data(self, graph: RunGraph) -> dict:
        """Return elements, paths, and metadata for the JS frontend (used by /api/graph)."""
        node_cy_map = self._compute_node_cy_map(graph)
        return {
            "elements":     self._build_elements(graph, node_cy_map),
            "paths":        self._build_paths_data(graph, node_cy_map),
            "test_case_id": graph.test_case_id,
            "description":  graph.description or "",
        }

    def generate_html(self, graph: RunGraph, cases: list[str] | None = None) -> str:
        data       = self.build_graph_data(graph)
        cases_list = sorted(cases) if cases else [graph.test_case_id]

        html = _HTML_TEMPLATE
        html = html.replace("__TITLE__",             f"Run Graph — {graph.test_case_id}")
        html = html.replace("__TEST_CASE_ID__",      graph.test_case_id)
        html = html.replace("__DESCRIPTION__",       graph.description or "")
        html = html.replace("__TEST_CASE_ID_JSON__", json.dumps(graph.test_case_id))
        html = html.replace("__ELEMENTS_JSON__",     json.dumps(data["elements"]))
        html = html.replace("__PATHS_JSON__",        json.dumps(data["paths"]))
        html = html.replace("__DESCRIPTION_JSON__",  json.dumps(data["description"]))
        html = html.replace("__CASES_JSON__",        json.dumps(cases_list))
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
                "cost":           node.cost.model_dump(exclude_none=True) if node.cost else None,
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
