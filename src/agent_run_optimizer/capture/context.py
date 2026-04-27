from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from agent_run_optimizer.capture.config import RunCaptureConfig
from agent_run_optimizer.graph.models import EdgeType, RunEdge, RunGraph, RunNode, RunPath
from agent_run_optimizer.storage.base import RunStoreBase


class RunCapture:
    """
    Accumulates nodes and edges for one execution path and saves it to a RunStoreBase.

    Two usage patterns:

    Direct (no OTel):
        cap = RunCapture(test_case_id="task", store=store, path_id="run-001")
        cap.add_node(RunNode(id="llm-1", type=NodeType.LLM, label="Analyse"))
        cap.add_node(RunNode(id="tool-bash-1", type=NodeType.TOOL, label="bash"))
        cap.add_edge("llm-1", "tool-bash-1")
        cap.finish(outcome="success")

    OTel context manager:
        with RunCapture(test_case_id="task", store=store) as cap:
            with cap.tracer.start_as_current_span("llm-call", attributes={...}):
                result = llm_call()
    """

    def __init__(
        self,
        test_case_id: str,
        store: RunStoreBase,
        *,
        path_id: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
        config: RunCaptureConfig | None = None,
    ) -> None:
        self.test_case_id = test_case_id
        self.store = store
        self.path_id = path_id or _auto_path_id()
        self.description = description
        self.tags = tags or []
        self.config = config or RunCaptureConfig()
        self._started_at: datetime = datetime.now(timezone.utc)
        self._nodes: dict[str, RunNode] = {}
        self._edges: list[RunEdge] = []
        self._sequence: list[str] = []
        self._provider: TracerProvider | None = None

    # ── Direct recording ──────────────────────────────────────────────

    def add_node(self, node: RunNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._sequence:
            self._sequence.append(node.id)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.SEQUENTIAL,
        label: str = "",
    ) -> None:
        self._edges.append(RunEdge(source=source_id, target=target_id, type=edge_type, label=label))

    # ── OTel instrumentation ──────────────────────────────────────────

    def setup_otel(self) -> TracerProvider:
        from agent_run_optimizer.capture.otel_exporter import RunSpanExporter
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(RunSpanExporter(self)))
        return self._provider

    @property
    def tracer(self) -> trace.Tracer:
        if self._provider is None:
            self.setup_otel()
        return self._provider.get_tracer("agent-run-optimizer")

    # ── Finalise ─────────────────────────────────────────────────────

    def finish(self, outcome: str = "unknown", duration_ms: int | None = None) -> RunGraph:
        if self._provider:
            self._provider.force_flush()

        ended_at = datetime.now(timezone.utc)
        if duration_ms is None:
            duration_ms = int((ended_at - self._started_at).total_seconds() * 1000)

        path = RunPath(
            path_id=self.path_id,
            outcome=outcome,
            timestamp=self._started_at,
            duration_ms=duration_ms,
            node_sequence=list(self._sequence),
            edges=list(self._edges),
        )

        try:
            graph = self.store.load(self.test_case_id)
            for nid, node in self._nodes.items():
                if nid not in graph.nodes:
                    graph.nodes[nid] = node
            graph.paths = [p for p in graph.paths if p.path_id != self.path_id]
            graph.paths.append(path)
        except FileNotFoundError:
            graph = RunGraph(
                test_case_id=self.test_case_id,
                description=self.description,
                created_at=self._started_at,
                tags=self.tags,
                nodes=self._nodes,
                paths=[path],
            )

        self.store.save(graph)
        return graph

    # ── Context manager ───────────────────────────────────────────────

    def __enter__(self) -> RunCapture:
        self.setup_otel()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finish(outcome="failure" if exc_type else "unknown")
        return False


# ── Helpers ───────────────────────────────────────────────────────────

def _auto_path_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    salt = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
    return f"run-{ts}-{salt}"


def messages_hash(messages: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(messages, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
