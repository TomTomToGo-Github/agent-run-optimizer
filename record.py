#!/usr/bin/env python3
"""
record.py — start a Claude Code session with automatic run capture.

Usage:
    uv run python record.py
    uv run python record.py --task my-task-name
    uv run python record.py --task my-task-name --no-viz

Flow:
  1. Loads .env from the repo root
  2. Sets AI_REPRO_TASK so hooks write to the right YAML
  3. Spawns the `claude` CLI in this terminal (fully interactive)
  4. After the session ends, opens the run visualization automatically
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ── Load .env before anything else ───────────────────────────────────────
_ROOT = Path(__file__).parent
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass  # dotenv optional — rely on shell env


def _resolve_task(arg: str | None) -> str:
    task = arg or os.environ.get("AI_REPRO_TASK", "").strip()
    if not task:
        print("Error: task name is required.")
        print("  Set AI_REPRO_TASK in .env  — or pass  --task <name>")
        sys.exit(1)
    return task


def _launch_claude(task: str, runs_dir: str) -> int:
    """Spawn the claude CLI interactively; return its exit code."""
    env = {
        **os.environ,
        "AI_REPRO_TASK":     task,
        "AI_REPRO_RUNS_DIR": runs_dir,
    }
    print()
    print(f"  Recording  : {task}")
    print(f"  Output     : {runs_dir}/{task}/")
    print(f"  Stop       : type /exit or press Ctrl-C in the Claude session")
    print()

    try:
        result = subprocess.run(["claude"], env=env)
        return result.returncode
    except FileNotFoundError:
        print("\nError: 'claude' command not found.")
        print("Install Claude Code:  https://claude.ai/download")
        sys.exit(1)


def _open_viz(task: str, runs_dir: str, port: int | None) -> None:
    """Launch the visualization server for the recorded task."""
    run_dir = Path(runs_dir) / task
    if not run_dir.exists() or not any(run_dir.glob("*.yaml")):
        print(f"\nNo run data found at {run_dir}/ — nothing to visualize.")
        return

    print("\n  Session saved. Opening visualization …\n")
    cmd = [
        sys.executable, str(_ROOT / "run_example.py"),
        "--runs-dir", runs_dir,
    ]
    if port:
        cmd += ["--port", str(port)]
    subprocess.run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record a Claude Code session and visualize it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task",     default=None,       help="Test-case ID (default: AI_REPRO_TASK from .env)")
    parser.add_argument("--runs-dir", default=None,       help="Output directory (default: AI_REPRO_RUNS_DIR from .env, or 'agent_runs')")
    parser.add_argument("--port",     type=int,           help="Visualization server port (auto if omitted)")
    parser.add_argument("--no-viz",   action="store_true", help="Skip the visualization after the session")
    args = parser.parse_args()

    task     = _resolve_task(args.task)
    runs_dir = args.runs_dir or os.environ.get("AI_REPRO_RUNS_DIR", "agent_runs").strip()

    _launch_claude(task, runs_dir)

    if not args.no_viz:
        _open_viz(task, runs_dir, args.port)


if __name__ == "__main__":
    main()
