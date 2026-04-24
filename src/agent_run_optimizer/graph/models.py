from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    HUMAN = "human"
    CHECKPOINT = "checkpoint"


class EdgeType(str, Enum):
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    RETRY = "retry"
    PARALLEL = "parallel"


class NodeCost(BaseModel):
    latency_ms: float | None = None
    cost_usd: float | None = None


class LLMCost(NodeCost):
    kind: Literal["llm"] = "llm"
    input_tokens: int | None = None
    output_tokens: int | None = None


class ToolCost(NodeCost):
    kind: Literal["tool"] = "tool"


class HumanCost(NodeCost):
    kind: Literal["human"] = "human"


class CheckpointCost(NodeCost):
    kind: Literal["checkpoint"] = "checkpoint"


class RunNode(BaseModel):
    id: str
    type: NodeType
    label: str
    is_fixpoint: bool = False
    user_important: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    cost: NodeCost | None = None


class RunEdge(BaseModel):
    source: str
    target: str
    type: EdgeType = EdgeType.SEQUENTIAL
    label: str = ""


class RunPath(BaseModel):
    path_id: str
    outcome: str = "unknown"
    timestamp: datetime | None = None
    duration_ms: int | None = None
    node_sequence: list[str]
    edges: list[RunEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunGraph(BaseModel):
    test_case_id: str
    description: str = ""
    created_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    nodes: dict[str, RunNode] = Field(default_factory=dict)
    paths: list[RunPath] = Field(default_factory=list)