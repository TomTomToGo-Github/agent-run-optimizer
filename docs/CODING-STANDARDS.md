# Coding Standards
*A brief, human- and agent-friendly introduction to coding standards in this repository*

To read about deterministic formatting and linting, see [DEVTOOLS.md](DEVTOOLS.md).

## Multi-Platform Development; Linux Deployment

Code contributors develop on Windows, Linux, and macOS. 
All source code contributions must be cross-platform compatible.

The deployment exclusively runs on Linux. Deployment scripts, 
Dockerfiles, and CI pipelines should assume Linux.

### Path Handling

Always use `pathlib.Path` for file paths:

```python
# ✅ Correct
from pathlib import Path

config_path = Path(__file__).parent / "config/settings.yaml"

# ❌ Avoid - breaks on Windows
config_path = os.path.dirname(__file__) + "/config/settings.yaml"
```

## Type Hints

Always use native type hints. Avoid the `typing` module unless necessary:

```python
# ✅ Correct
def process(data: dict[str, list[int]], flag: bool | None = None) -> str:
    ...


# ❌ Avoid
from typing import Optional, Dict, List


def process(data: Dict[str, List[int]], flag: Optional[bool] = None) -> str:
    ...
```
