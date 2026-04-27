#!/usr/bin/env python3
"""
Called by Claude Code .claude/settings.json hooks. Reads JSON payload from stdin.

Usage — add to .claude/settings.json:

    {
      "hooks": {
        "PreToolUse":  [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py pre-tool"}]}],
        "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}],
        "Stop":        [{"hooks": [{"type": "command", "command": "python hooks/capture_hook.py stop"}]}]
      }
    }

Environment variables:
    AI_REPRO_TASK      required  test-case-id written to the YAML
    AI_REPRO_RUNS_DIR  optional  output directory (default: agent_runs)
    AI_REPRO_DESC      optional  human-readable description for new graphs
    AI_REPRO_SESSION_DIR  optional  session state directory (default: ~/.ai-repro/sessions)
"""
from __future__ import annotations

import json
import os
import sys

# Allow running directly from the repo root without `pip install`
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Load .env from repo root (does not override already-set env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass



def _read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: capture_hook.py <pre-tool|post-tool|stop>", file=sys.stderr)
        sys.exit(1)

    event = sys.argv[1].lower()
    test_case_id = os.environ.get("AI_REPRO_TASK", "").strip()
    runs_dir = os.environ.get("AI_REPRO_RUNS_DIR", "agent_runs").strip()
    description = os.environ.get("AI_REPRO_DESC", "").strip()

    try:
        payload = _read_payload()
        if not payload:
            return

        from agent_run_optimizer.capture.claude_code_hooks import (
            process_post_tool,
            process_pre_tool,
            process_stop,
        )

        if event == "pre-tool":
            process_pre_tool(payload)
        elif event == "post-tool":
            process_post_tool(payload)
        elif event == "stop":
            if not test_case_id:
                print(
                    "capture_hook: AI_REPRO_TASK not set — skipping stop capture",
                    file=sys.stderr,
                )
                return
            process_stop(
                payload,
                test_case_id=test_case_id,
                runs_dir=runs_dir,
                description=description,
            )
        else:
            print(f"capture_hook: unknown event '{event}'", file=sys.stderr)

    except Exception as exc:  # never block Claude Code
        print(f"capture_hook error ({event}): {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
