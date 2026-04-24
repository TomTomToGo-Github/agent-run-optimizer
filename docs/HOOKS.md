# Claude Code Hooks

Hooks let Claude Code automatically capture every tool call and conversation stop into a run graph — no changes to agent code needed.

## Setup

**1. Set the task ID** so the hook knows which YAML file to write to:

```bash
export AI_REPRO_TASK=my-task-name
```

**2. Add hooks to `.claude/settings.json`:**

```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py pre-tool"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py post-tool"}]}],
    "Stop":        [{"hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}]
  }
}
```

## What gets captured

| Hook | Produces |
|---|---|
| `PreToolUse` | Tool node start timestamp |
| `PostToolUse` | Tool node with name, args, result, latency |
| `Stop` | LLM node reconstructed from conversation history; path finalised and written to `runs/<task-id>.yaml` |

## Hook script

`hooks/capture_hook.py` reads the hook payload from stdin (JSON), converts it to a `RunNode`, and appends it to the active `RunGraph` for the current `AI_REPRO_TASK`.

> **Status:** `hooks/capture_hook.py` is planned but not yet implemented. See `specs/BACKEND_MISSING.md` for the full capture layer roadmap.