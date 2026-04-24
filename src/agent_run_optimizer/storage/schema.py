from __future__ import annotations

from datetime import datetime

from agent_run_optimizer.graph.models import EdgeType, NodeType, RunEdge, RunGraph, RunNode, RunPath

SCHEMA_VERSION = "1"


def graph_to_dict(graph: RunGraph) -> dict:
    return {
        "_schema_version": SCHEMA_VERSION,
        "test_case": {
            "id": graph.test_case_id,
            "description": graph.description,
            "created_at": graph.created_at.isoformat() if graph.created_at else None,
            "tags": graph.tags,
        },
        "nodes": {
            node_id: {
                "type": node.type.value,
                "label": node.label,
                "is_fixpoint": node.is_fixpoint,
                "user_important": node.user_important,
                "metadata": node.metadata,
            }
            for node_id, node in graph.nodes.items()
        },
        "paths": [
            {
                "path_id": path.path_id,
                "outcome": path.outcome,
                "timestamp": path.timestamp.isoformat() if path.timestamp else None,
                "duration_ms": path.duration_ms,
                "node_sequence": path.node_sequence,
                "edges": [
                    {
                        "from": edge.source,
                        "to": edge.target,
                        "type": edge.type.value,
                        "label": edge.label,
                    }
                    for edge in path.edges
                ],
                "metadata": path.metadata,
            }
            for path in graph.paths
        ],
    }


def dict_to_graph(data: dict) -> RunGraph:
    tc = data.get("test_case", {})

    nodes: dict[str, RunNode] = {}
    for node_id, nd in data.get("nodes", {}).items():
        nodes[node_id] = RunNode(
            id=node_id,
            type=NodeType(nd["type"]),
            label=nd.get("label", node_id),
            is_fixpoint=nd.get("is_fixpoint", False),
            user_important=nd.get("user_important", False),
            metadata=nd.get("metadata", {}),
        )

    paths: list[RunPath] = []
    for pd in data.get("paths", []):
        edges = [
            RunEdge(
                source=e["from"],
                target=e["to"],
                type=EdgeType(e.get("type", "sequential")),
                label=e.get("label", ""),
            )
            for e in pd.get("edges", [])
        ]
        ts = pd.get("timestamp")
        paths.append(
            RunPath(
                path_id=pd["path_id"],
                outcome=pd.get("outcome", "unknown"),
                timestamp=datetime.fromisoformat(ts) if ts else None,
                duration_ms=pd.get("duration_ms"),
                node_sequence=pd.get("node_sequence", []),
                edges=edges,
                metadata=pd.get("metadata", {}),
            )
        )

    created_at = tc.get("created_at")
    return RunGraph(
        test_case_id=tc.get("id", "unknown"),
        description=tc.get("description", ""),
        created_at=datetime.fromisoformat(created_at) if created_at else None,
        tags=tc.get("tags", []),
        nodes=nodes,
        paths=paths,
    )