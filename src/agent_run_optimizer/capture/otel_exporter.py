from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agent_run_optimizer.graph.models import (
    CheckpointCost,
    EdgeType,
    HumanCost,
    LLMCost,
    NodeType,
    RunEdge,
    RunNode,
    ToolCost,
)

if TYPE_CHECKING:
    from agent_run_optimizer.capture.context import RunCapture


# ── OTel attribute keys ───────────────────────────────────────────────
# Follows OpenTelemetry GenAI semantic conventions where they exist,
# with ai.* extensions for our own fields.
#
#   ai.node_type          "llm" | "tool" | "human" | "checkpoint"
#   ai.node_id            override the auto-generated node id
#   ai.label              human-readable label for the node
#   ai.is_fixpoint        bool — mark as required step
#   ai.sequence           int  — position in the run (used in auto-id)
#   ai.model              model name for LLM nodes
#   ai.temperature        float
#   ai.messages_hash      SHA-256[:16] of the input messages list
#   ai.tool_name          tool name for tool nodes
#   ai.tool_input_hash    SHA-256[:12] of the tool input dict
#   ai.tool_result        truncated tool output (≤500 chars)
#   ai.latency_ms         float wall-clock latency
#   ai.cost_usd           float estimated cost
#   gen_ai.usage.input_tokens   int
#   gen_ai.usage.output_tokens  int


class RunSpanExporter(SpanExporter):
    """Converts completed OTel spans into RunNode/RunEdge objects via RunCapture."""

    def __init__(self, capture: RunCapture) -> None:
        self._capture = capture
        # span_id (int) → node_id — used to wire parent→child edges
        self._span_to_node: dict[int, str] = {}

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            node = _span_to_node(span)
            if node is None:
                continue
            self._capture.add_node(node)

            # Wire sequential edge from parent span's node if present
            parent = span.parent
            if parent and parent.span_id in self._span_to_node:
                parent_nid = self._span_to_node[parent.span_id]
                seq = self._capture._sequence
                if len(seq) >= 2 and seq[-1] == node.id and seq[-2] == parent_nid:
                    self._capture.add_edge(parent_nid, node.id)
            elif len(self._capture._sequence) >= 2:
                prev = self._capture._sequence[-2]
                self._capture.add_edge(prev, node.id)

            self._span_to_node[span.context.span_id] = node.id
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


# ── Span → RunNode conversion ─────────────────────────────────────────

_tool_counters: dict[str, int] = {}


def _span_to_node(span: ReadableSpan) -> RunNode | None:
    attrs = dict(span.attributes or {})
    try:
        node_type = NodeType(attrs.get("ai.node_type", "tool"))
    except ValueError:
        node_type = NodeType.TOOL

    node_id = attrs.get("ai.node_id") or _auto_node_id(span, node_type, attrs)
    label = attrs.get("ai.label") or _auto_label(node_type, attrs)

    return RunNode(
        id=str(node_id),
        type=node_type,
        label=str(label),
        is_fixpoint=bool(attrs.get("ai.is_fixpoint", False)),
        metadata=_metadata(node_type, attrs, span),
        cost=_cost(node_type, attrs),
    )


def _auto_node_id(span: ReadableSpan, node_type: NodeType, attrs: dict) -> str:
    if node_type == NodeType.LLM:
        seq = attrs.get("ai.sequence", 1)
        return f"llm-{seq}"
    if node_type == NodeType.TOOL:
        name = str(attrs.get("ai.tool_name", span.name or "tool")).replace(" ", "-").lower()
        _tool_counters[name] = _tool_counters.get(name, 0) + 1
        n = _tool_counters[name]
        return f"tool-{name}" if n == 1 else f"tool-{name}-{n}"
    if node_type == NodeType.HUMAN:
        return f"human-{span.context.span_id & 0xFFFFFFFF:08x}"
    return f"checkpoint-{span.context.span_id & 0xFFFFFFFF:08x}"


def _auto_label(node_type: NodeType, attrs: dict) -> str:
    if node_type == NodeType.TOOL:
        return str(attrs.get("ai.tool_name", "Tool call"))
    if node_type == NodeType.LLM:
        return str(attrs.get("ai.model", "LLM call"))
    return node_type.value.title()


def _cost(node_type: NodeType, attrs: dict):
    in_tok = attrs.get("gen_ai.usage.input_tokens")
    out_tok = attrs.get("gen_ai.usage.output_tokens")
    lat = attrs.get("ai.latency_ms")
    usd = attrs.get("ai.cost_usd")

    kw = {
        "latency_ms": float(lat) if lat is not None else None,
        "cost_usd":   float(usd) if usd is not None else None,
    }
    has_base = any(v is not None for v in kw.values())

    if node_type == NodeType.LLM:
        llm_kw = {
            "input_tokens":  int(in_tok)  if in_tok  is not None else None,
            "output_tokens": int(out_tok) if out_tok is not None else None,
        }
        if has_base or any(v is not None for v in llm_kw.values()):
            return LLMCost(**kw, **llm_kw)
    elif node_type == NodeType.TOOL and has_base:
        return ToolCost(**kw)
    elif node_type == NodeType.HUMAN and has_base:
        return HumanCost(**kw)
    elif node_type == NodeType.CHECKPOINT and has_base:
        return CheckpointCost(**kw)
    return None


def _metadata(node_type: NodeType, attrs: dict, span: ReadableSpan) -> dict:
    meta: dict = {}
    if node_type == NodeType.LLM:
        for k in ("ai.model", "ai.temperature", "ai.messages_hash"):
            if k in attrs:
                meta[k.split(".")[-1]] = attrs[k]
        for k in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"):
            if k in attrs:
                meta[k.split(".")[-1]] = attrs[k]
    elif node_type == NodeType.TOOL:
        for k in ("ai.tool_name", "ai.tool_input_hash", "ai.tool_result"):
            if k in attrs:
                meta[k.split(".")[-1]] = attrs[k]
    return meta
