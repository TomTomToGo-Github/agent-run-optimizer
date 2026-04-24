from __future__ import annotations

from datetime import datetime

from agent_run_optimizer.graph.models import EdgeType, NodeType, RunEdge, RunGraph, RunNode, RunPath

SCHEMA_VERSION = "2"


def graph_to_path_dicts(graph: RunGraph) -> list[dict]:
    """Convert a RunGraph into one dict per path for per-path YAML files."""
    result = []
    for path in graph.paths:
        path_node_ids = set(path.node_sequence)
        result.append({
            "_schema_version": SCHEMA_VERSION,
            "test_case_id":    graph.test_case_id,
            "description":     graph.description,
            "created_at":      graph.created_at.date().isoformat() if graph.created_at else None,
            "tags":            graph.tags,
            "path_id":         path.path_id,
            "outcome":         path.outcome,
            "timestamp":       path.timestamp.isoformat() if path.timestamp else None,
            "duration_ms":     path.duration_ms,
            "metadata":        path.metadata,
            "node_sequence":   path.node_sequence,
            "edges":           [_edge_to_dict(e) for e in path.edges],
            "nodes": {
                nid: _node_to_dict(n)
                for nid, n in graph.nodes.items()
                if nid in path_node_ids
            },
        })
    return result


def path_dicts_to_graph(path_dicts: list[dict]) -> RunGraph:
    """Merge per-path dicts into a RunGraph (alphabetical load order; later files win for shared node state)."""
    if not path_dicts:
        raise ValueError("No path dicts provided")

    first = path_dicts[0]
    all_nodes: dict[str, RunNode] = {}
    all_paths: list[RunPath] = []

    for data in path_dicts:
        for nid, nd in data.get("nodes", {}).items():
            all_nodes[nid] = RunNode(
                id=nid,
                type=NodeType(nd["type"]),
                label=nd.get("label", nid),
                is_fixpoint=nd.get("is_fixpoint", False),
                user_important=nd.get("user_important", False),
                metadata=nd.get("metadata", {}),
            )
        edges = [
            RunEdge(
                source=e["from"],
                target=e["to"],
                type=EdgeType(e.get("type", "sequential")),
                label=e.get("label", ""),
            )
            for e in data.get("edges", [])
        ]
        ts = data.get("timestamp")
        all_paths.append(RunPath(
            path_id=data["path_id"],
            outcome=data.get("outcome", "unknown"),
            timestamp=datetime.fromisoformat(ts) if ts else None,
            duration_ms=data.get("duration_ms"),
            node_sequence=data.get("node_sequence", []),
            edges=edges,
            metadata=data.get("metadata", {}),
        ))

    created_at_str = first.get("created_at")
    return RunGraph(
        test_case_id=first.get("test_case_id", "unknown"),
        description=first.get("description", ""),
        created_at=datetime.fromisoformat(created_at_str) if created_at_str else None,
        tags=first.get("tags", []),
        nodes=all_nodes,
        paths=all_paths,
    )


def metadata_md(graph: RunGraph) -> str:
    """Generate a human-readable METADATA.md for a test case folder."""
    _OUTCOME_ICON = {"success": "✅", "failure": "❌", "partial": "⚠️", "unknown": "❓"}

    lines = [
        f"# {graph.test_case_id}",
        "",
        graph.description or "",
        "",
        f"**Created:** {graph.created_at.date() if graph.created_at else 'unknown'}  ",
    ]
    if graph.tags:
        lines.append("**Tags:** " + ", ".join(f"`{t}`" for t in graph.tags))
    lines += ["", "---", "", "## Nodes", ""]
    lines += [
        "| ID | Type | Label | Required Step | User-marked |",
        "|---|---|:---|:---:|:---:|",
    ]
    for nid, n in graph.nodes.items():
        lines.append(
            f"| {nid} | {n.type.value} | {n.label} | "
            f"{'✓' if n.is_fixpoint else ''} | {'✓' if n.user_important else ''} |"
        )
    lines += ["", "---", "", "## Runs", ""]
    lines += ["| Run | Outcome | Duration | Steps |", "|---|---|---|---|"]
    for p in graph.paths:
        icon = _OUTCOME_ICON.get(p.outcome, "❓")
        dur = f"{p.duration_ms / 1000:.1f}s" if p.duration_ms else "—"
        lines.append(
            f"| [{p.path_id}]({p.path_id}.yaml)"
            f" | {icon} {p.outcome} | {dur} | {len(p.node_sequence)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _node_to_dict(n: RunNode) -> dict:
    return {
        "type":           n.type.value,
        "label":          n.label,
        "is_fixpoint":    n.is_fixpoint,
        "user_important": n.user_important,
        "metadata":       n.metadata,
    }


def _edge_to_dict(e: RunEdge) -> dict:
    d: dict = {"from": e.source, "to": e.target}
    if e.type != EdgeType.SEQUENTIAL:
        d["type"] = e.type.value
    if e.label:
        d["label"] = e.label
    return d