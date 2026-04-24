# Dev Tools

## Setup

```bash
uv sync                      # create venv and install all dependencies
```

## Running

```bash
# Start the interactive graph visualization (opens browser)
uv run python run_example.py --test-case incident-resolution

# CLI (once implemented)
uv run ai-repro --help
```

## Tests

```bash
uv run pytest                              # all tests
uv run pytest tests/test_models.py        # single file
uv run pytest -x                          # stop on first failure
```

## Linting & Formatting

```bash
uv run flake8 src/ tests/
uv run isort --check-only src/ tests/
uv run black --check src/ tests/

# Auto-fix formatting
uv run isort src/ tests/
uv run black src/ tests/
```

## Environment

- Python version: see `.python-version`
- Dependencies: `pyproject.toml` → `[dependencies]`
- Dev dependencies: `pyproject.toml` → `[dependency-groups] dev`