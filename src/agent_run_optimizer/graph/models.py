from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

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


class RunNode(BaseModel):
    id: str
    type: NodeType
    label: str
    is_fixpoint: bool = False
    user_important: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


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