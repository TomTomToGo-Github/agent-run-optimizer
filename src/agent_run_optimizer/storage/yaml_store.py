from __future__ import annotations

from pathlib import Path

import yaml

from agent_run_optimizer.graph.models import RunGraph
from agent_run_optimizer.storage.base import RunStoreBase
from agent_run_optimizer.storage.schema import graph_to_path_dicts, metadata_md, path_dicts_to_graph


class YAMLRunStore(RunStoreBase):
    """Stores each run path as a separate YAML file under agent_runs/<test_case_id>/<path_id>.yaml."""

    def __init__(self, runs_dir: str | Path = "agent_runs"):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _dir(self, test_case_id: str) -> Path:
        return self.runs_dir / test_case_id

    def load(self, test_case_id: str) -> RunGraph:
        case_dir = self._dir(test_case_id)
        path_files = sorted(case_dir.glob("*.yaml"))
        if not path_files:
            raise FileNotFoundError(f"No YAML files found in {case_dir}")
        path_dicts = []
        for f in path_files:
            with open(f, encoding="utf-8") as fh:
                path_dicts.append(yaml.safe_load(fh))
        return path_dicts_to_graph(path_dicts)

    def save(self, graph: RunGraph) -> None:
        case_dir = self._dir(graph.test_case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        for path_dict in graph_to_path_dicts(graph):
            path_file = case_dir / f"{path_dict['path_id']}.yaml"
            with open(path_file, "w", encoding="utf-8") as f:
                yaml.dump(path_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        with open(case_dir / "METADATA.md", "w", encoding="utf-8") as f:
            f.write(metadata_md(graph))

    def sync_node_states(self, test_case_id: str, updates: dict[str, dict]) -> None:
        graph = self.load(test_case_id)
        for node_id, state in updates.items():
            if node_id in graph.nodes:
                graph.nodes[node_id] = graph.nodes[node_id].model_copy(update=state)
        self.save(graph)

    def list_test_cases(self) -> list[str]:
        return [d.name for d in self.runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]