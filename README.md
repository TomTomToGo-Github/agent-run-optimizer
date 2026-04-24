# agent-run-optimizer

Make LLM agent executions observable, replayable, and analyzable via graph-based run tracking.

Each run of an LLM task = one path in a graph. Repeat the same call = another path. Overlay many runs = a probabilistic map of your agent's behavior space.

## Prerequisites

### Python

Install Python 3.12 via the [Python extension for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python):

1. Open VS Code → Extensions (`Ctrl+Shift+X`) → search **Python** → install the Microsoft extension
2. Open the Command Palette (`Ctrl+Shift+P`) → **Python: Select Interpreter**
3. If no 3.12 interpreter is listed, choose **Enter interpreter path** → **Find** and locate your Python 3.12 installation, or use **Python: Install Python** from the palette to download it via the extension

Alternatively, install Python 3.12 directly from [python.org/downloads](https://www.python.org/downloads/) and restart VS Code.

### uv

[uv](https://docs.astral.sh/uv/) is the package and project manager used by this repo.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installing. Verify with `uv --version`.

---

## Setup

```bash
uv sync
```

## Development

```bash
uv run pytest
uv run black src/ tests/
uv run isort src/ tests/
uv run flake8 src/ tests/
```

See [specs/PLAN.md](specs/PLAN.md) for the implementation roadmap and [specs/BRAINSTORM.md](specs/BRAINSTORM.md) for the full concept.
For all documentation see [CLAUDE.md](CLAUDE.md).