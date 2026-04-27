# Claude Code Hooks

Hooks let Claude Code automatically capture every tool call and conversation stop into a run graph — no changes to agent code needed.

## Setup

**1. Set the task ID** so the hook knows which YAML file to write to:

Bash:
```bash
export AI_REPRO_TASK=my-task-name
export AI_REPRO_RUNS_DIR=agent_runs   # optional
```

PowerShell:
```powershell
$env:AI_REPRO_TASK = "my-task-name"
$env:AI_REPRO_RUNS_DIR = "agent_runs"   # optional
```

**2. Add hooks to `.claude/settings.json`:**

Bash:
```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py pre-tool"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py post-tool"}]}],
    "Stop":        [{"hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}]
  }
}
```

PowerShell:
```json
{
  "hooks": {
    "PreToolUse":  [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py pre-tool"}]}],
    "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py post-tool"}]}],
    "Stop":        [{"hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}]
  }
}
```

**3. Optional env vars:**

| Variable | Default | Purpose |
|---|---|---|
| `AI_REPRO_TASK` | *(required for stop)* | Test-case ID written to the YAML |
| `AI_REPRO_RUNS_DIR` | `agent_runs` | Output directory |
| `AI_REPRO_DESC` | `""` | Human-readable description for new graphs |
| `AI_REPRO_SESSION_DIR` | `~/.ai-repro/sessions` | Where intermediate session state is kept |

## What gets captured

| Hook | Produces |
|---|---|
| `PreToolUse` | Tool node start timestamp (persisted to session file) |
| `PostToolUse` | Tool node with name, args, truncated result, latency |
| `Stop` | LLM nodes reconstructed from conversation history; path finalised and written to `<runs_dir>/<task-id>/<path-id>.yaml` |

## How it works

```
PreToolUse  → hooks/capture_hook.py pre-tool
                └─ process_pre_tool()  records start timestamp

PostToolUse → hooks/capture_hook.py post-tool
                └─ process_post_tool() records tool end + computes latency

Stop        → hooks/capture_hook.py stop
                └─ process_stop()      walks conversation history
                                       interleaves LLM turns + tool nodes
                                       saves YAML via RunCapture
```

Session state is stored between hook invocations in `$AI_REPRO_SESSION_DIR/{session_id}.json` and deleted after `Stop` completes.

## Hook script

`hooks/capture_hook.py` is the CLI entry point. It reads the hook payload from stdin (JSON), dispatches to the appropriate processor in `src/agent_run_optimizer/capture/claude_code_hooks.py`, and never raises — errors are printed to stderr so Claude Code is never blocked.

The script inserts `src/` into `sys.path` automatically, so no `pip install` is required as long as the repo root is the working directory.
