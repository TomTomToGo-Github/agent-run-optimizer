# CLAUDE.md

## Quick Commands

```bash
uv sync                                                              # install dependencies
uv run python run_example.py --test-case incident-resolution        # launch interactive viz
uv run pytest                                                        # run tests
```

Full dev commands → [`docs/DEVTOOLS.md`](docs/DEVTOOLS.md)

---

## Documentation Index

### Specs

| File | What it covers |
|---|---|
| [`specs/BACKEND_README.md`](specs/BACKEND_README.md) | Module layout, data model, storage API, capture usage, visualization |
| [`specs/BACKEND_IMPLEMENTATION_PROGRESS.md`](specs/BACKEND_IMPLEMENTATION_PROGRESS.md) | Every backend feature that is fully implemented |
| [`specs/BACKEND_MISSING.md`](specs/BACKEND_MISSING.md) | Planned backend features not yet started (capture, analysis, CLI, replay) |
| [`specs/UI_README.md`](specs/UI_README.md) | Interactive graph UI — layout, interactions, sync button |
| [`specs/UI_IMPLEMENTATION_PROGRESS.md`](specs/UI_IMPLEMENTATION_PROGRESS.md) | Every UI feature that is fully implemented |
| [`specs/UI_MISSING.md`](specs/UI_MISSING.md) | Planned UI features not yet started |
| [`specs/PLAN.md`](specs/PLAN.md) | Phase-by-phase implementation plan with design decisions |
| [`specs/BRAINSTORM.md`](specs/BRAINSTORM.md) | Original design exploration — node types, capture layer, analysis ideas |

### Docs

| File | What it covers |
|---|---|
| [`docs/DEVTOOLS.md`](docs/DEVTOOLS.md) | All dev commands: uv, pytest, lint, format, run |
| [`docs/HOOKS.md`](docs/HOOKS.md) | Claude Code hooks setup for automatic run capture |
| [`docs/CODING-STANDARDS.md`](docs/CODING-STANDARDS.md) | Cross-platform paths, type hints, naming conventions |
| [`docs/STYLE.md`](docs/STYLE.md) | Docstrings, git branch and commit naming |

### Example Data

| File | What it covers |
|---|---|
| [`agent_runs/incident-resolution/`](agent_runs/test-incident-resolution/) | Example run graph: 3 paths, 12 nodes, 3 fixpoints — one YAML per path + METADATA.md |