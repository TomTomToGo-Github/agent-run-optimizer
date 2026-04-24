from __future__ import annotations

from pathlib import Path

import yaml

from agent_run_optimizer.graph.models import RunGraph
from agent_run_optimizer.storage.base import RunStoreBase
from agent_run_optimizer.storage.schema import dict_to_graph, graph_to_dict


class YAMLRunStore(RunStoreBase):
    def __init__(self, runs_dir: str | Path = "runs"):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _file(self, test_case_id: str) -> Path:
        return self.runs_dir / f"{test_case_id}.yaml"

    def load(self, test_case_id: str) -> RunGraph:
        with open(self._file(test_case_id), encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return dict_to_graph(data)

    def save(self, graph: RunGraph) -> None:
        with open(self._file(graph.test_case_id), "w", encoding="utf-8") as f:
            yaml.dump(graph_to_dict(graph), f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def sync_node_states(self, test_case_id: str, updates: dict[str, dict]) -> None:
        graph = self.load(test_case_id)
        for node_id, state in updates.items():
            if node_id in graph.nodes:
                graph.nodes[node_id] = graph.nodes[node_id].model_copy(update=state)
        self.save(graph)

    def list_test_cases(self) -> list[str]:
        return [f.stem for f in self.runs_dir.glob("*.yaml")]