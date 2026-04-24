from __future__ import annotations

from abc import ABC, abstractmethod

from agent_run_optimizer.graph.models import RunGraph


class RunStoreBase(ABC):
    """Abstract persistence layer. Swap implementations without touching visualization or analysis code."""

    @abstractmethod
    def load(self, test_case_id: str) -> RunGraph: ...

    @abstractmethod
    def save(self, graph: RunGraph) -> None: ...

    @abstractmethod
    def sync_node_states(self, test_case_id: str, updates: dict[str, dict]) -> None:
        """Persist per-node UI state (e.g. user_important toggles) back to the store."""
        ...

    @abstractmethod
    def list_test_cases(self) -> list[str]: ...