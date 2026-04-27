# agent-run-optimizer

Make LLM agent executions observable, replayable, and analyzable via graph-based run tracking.

Each run of an LLM task = one path in a graph. Repeat the same task = another path. Overlay many runs = a probabilistic map of your agent's behavior space — which steps always happen, which vary, where it fails, and how much it costs.

---

## What it does

- **Captures** every Claude Code session automatically via hooks — no code changes needed
- **Stores** each run as a YAML file: nodes (LLM calls, tool invocations), edges, timing, token counts, cost
- **Visualizes** all runs for a task overlaid in an interactive graph in the browser
- **Compares** paths side-by-side: mark required steps, highlight deviations, toggle runs on/off

---

## Prerequisites

### Python 3.12+

Install via the [Python extension for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python) or directly from [python.org/downloads](https://www.python.org/downloads/).

### uv

[uv](https://docs.astral.sh/uv/) is the package manager used by this repo.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installing. Verify with `uv --version`.

### Claude Code

Install from [claude.ai/download](https://claude.ai/download). Verify with `claude --version`.

---

## Setup

```bash
uv sync
```

---

## Recording a Claude Code session

**1. Name your task** — edit `.env`:

```
AI_REPRO_TASK=my-task-name
```

**2. Start the session:**

```bash
uv run python record.py
```

Claude Code launches in your terminal with capture hooks active. Work normally, then exit with `/exit` or `Ctrl-C`. The run is saved automatically and the visualization opens in your browser when the session ends.

**Options:**

```
--task <name>    Override the task name from .env
--no-viz         Skip the visualization after the session ends
--port <n>       Visualization server port (auto-selected if omitted)
```

Each session appends a new path to `agent_runs/<task-name>/`. Run the same task multiple times to overlay paths and compare how the agent approached it differently each time.

---

## Visualization

Open the visualization for any recorded task at any time:

```bash
uv run python run_example.py
```

### What you see

All runs for a task are overlaid in a single graph. Nodes that appear in every run are shared; deviating steps sit in their own lane per path.

| Node shape | Meaning |
|---|---|
| Rounded rectangle | LLM call |
| Diamond | Tool invocation |
| Rectangle | Human interaction |
| Ellipse | Checkpoint |

**Gold border** = required step (fixpoint) — every successful path passes through this node.
**Pink border** = user-marked as important.

### Interactions

| Action | Effect |
|---|---|
| Hover path in sidebar | Highlight that path; everything else dims |
| Click path toggle `●` | Remove / restore the path from the graph |
| Hover `$` on a node | Cost popup: latency, tokens, USD |
| Click a node | Mark / unmark as required step; animates to center lane |
| Right-click a node | Mark / unmark as user-important |
| Sync to Store button | Write `is_fixpoint` and `user_important` state back to YAML |

---

## Project structure

```
record.py                  entry point — launches Claude + viz
run_example.py             visualization server only
.env                       task name and output directory
agent_runs/                captured run YAMLs (one folder per task)
hooks/capture_hook.py      Claude Code hook script
src/agent_run_optimizer/
  graph/models.py          RunNode, RunEdge, RunPath, RunGraph
  storage/                 YAMLRunStore + abstract RunStoreBase
  capture/                 RunCapture context manager, OTel exporter, hook processors
  viz/html.py              Cytoscape.js interactive HTML visualization
```

---

## Development

```bash
uv run pytest
uv run black src/ tests/
uv run isort src/ tests/
uv run flake8 src/ tests/
```

See [`docs/HOOKS.md`](docs/HOOKS.md) for hook configuration details and [`CLAUDE.md`](CLAUDE.md) for the full documentation index.
