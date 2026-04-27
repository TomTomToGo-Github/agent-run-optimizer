"""
Processes Claude Code hook payloads and saves a RunGraph YAML after each session.

Flow per Claude Code session:
  PreToolUse  → process_pre_tool()   records start timestamp to session file
  PostToolUse → process_post_tool()  records completed tool node (with latency)
  Stop        → process_stop()       reconstructs LLM turns from conversation,
                                     interleaves with tool nodes, saves YAML

Session state is persisted between the three hook invocations in:
  $AI_REPRO_SESSION_DIR/{session_id}.json   (default: ~/.ai-repro/sessions/)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agent_run_optimizer.capture.config import RunCaptureConfig
from agent_run_optimizer.capture.context import RunCapture, messages_hash
from agent_run_optimizer.graph.models import EdgeType, LLMCost, NodeType, RunEdge, RunNode, ToolCost
from agent_run_optimizer.storage.yaml_store import YAMLRunStore

_SESSION_DIR = Path(
    os.environ.get("AI_REPRO_SESSION_DIR", Path.home() / ".ai-repro" / "sessions")
)


# ── Session file helpers ──────────────────────────────────────────────

def _session_path(session_id: str) -> Path:
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSION_DIR / f"{session_id}.json"


def _load_session(session_id: str) -> dict:
    p = _session_path(session_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "events": [],
    }


def _save_session(data: dict) -> None:
    _session_path(data["session_id"]).write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8"
    )


# ── Public hook processors ────────────────────────────────────────────

def process_pre_tool(payload: dict) -> None:
    """PreToolUse: record start timestamp so we can compute latency later."""
    session = _load_session(payload["session_id"])
    session["events"].append({
        "kind":        "tool_start",
        "tool_use_id": payload.get("tool_use_id", ""),
        "tool_name":   payload.get("tool_name", ""),
        "tool_input":  payload.get("tool_input", {}),
        "started_at":  datetime.now(timezone.utc).isoformat(),
    })
    _save_session(session)


def process_post_tool(payload: dict) -> None:
    """PostToolUse: record completed tool call with latency."""
    session = _load_session(payload["session_id"])
    now = datetime.now(timezone.utc)
    tool_use_id = payload.get("tool_use_id", "")

    latency_ms: float | None = None
    for ev in reversed(session["events"]):
        if ev.get("kind") == "tool_start" and ev.get("tool_use_id") == tool_use_id:
            started = datetime.fromisoformat(ev["started_at"])
            latency_ms = (now - started).total_seconds() * 1000
            break

    raw_response = payload.get("tool_response", "")
    session["events"].append({
        "kind":            "tool_end",
        "tool_use_id":     tool_use_id,
        "tool_name":       payload.get("tool_name", ""),
        "tool_input":      payload.get("tool_input", {}),
        "tool_response":   str(raw_response)[:500] if raw_response else "",
        "latency_ms":      latency_ms,
        "ended_at":        now.isoformat(),
    })
    _save_session(session)


def _read_transcript(transcript_path: str) -> list[dict]:
    """Read the Claude Code JSONL transcript and return a list of message dicts."""
    messages = []
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") in ("user", "assistant") and "message" in obj:
                    messages.append(obj["message"])
    except (OSError, json.JSONDecodeError):
        pass
    return messages


def process_stop(
    payload: dict,
    test_case_id: str,
    runs_dir: str = "agent_runs",
    description: str = "",
) -> None:
    """
    Stop hook: reconstruct the full execution path from the transcript JSONL,
    interleave with captured tool timings, and save as a YAML run.

    Expected payload fields (Claude Code Stop hook):
      session_id       str
      transcript_path  str  path to the JSONL conversation file
      hook_event_name  str
    """
    session_id = payload["session_id"]
    session = _load_session(session_id)
    config = RunCaptureConfig()
    store = YAMLRunStore(runs_dir=runs_dir)

    # Index tool_end events by tool_use_id for O(1) lookup
    tool_end_by_id: dict[str, dict] = {
        ev["tool_use_id"]: ev
        for ev in session["events"]
        if ev.get("kind") == "tool_end"
    }

    nodes: dict[str, RunNode] = {}
    sequence: list[str] = []
    edges: list[RunEdge] = []
    tool_counters: dict[str, int] = {}
    llm_seq = 0
    conversation: list[dict] = _read_transcript(payload.get("transcript_path", ""))
    model = ""

    def _append(node: RunNode) -> None:
        if sequence:
            edges.append(RunEdge(source=sequence[-1], target=node.id))
        nodes[node.id] = node
        sequence.append(node.id)

    last_stop_reason = "unknown"
    for msg in conversation:
        role = msg.get("role")
        content = msg.get("content", [])
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        if role != "assistant":
            continue

        # Extract model from the first assistant message that has it
        if not model and msg.get("model"):
            model = msg["model"]

        if msg.get("stop_reason"):
            last_stop_reason = msg["stop_reason"]

        tool_use_blocks = [b for b in content if b.get("type") == "tool_use"]

        # ── LLM node for this assistant turn ─────────────────────────
        llm_seq += 1
        node_id = f"llm-{llm_seq}"
        usage = msg.get("usage", {})
        in_tok = usage.get("input_tokens")
        out_tok = usage.get("output_tokens")
        cost_usd = config.estimate_cost(model, in_tok or 0, out_tok or 0) if in_tok else None
        prior_msgs = conversation[: conversation.index(msg)]
        _append(RunNode(
            id=node_id,
            type=NodeType.LLM,
            label=_llm_label(llm_seq, bool(tool_use_blocks)),
            metadata={
                "model":         model,
                "messages_hash": messages_hash(prior_msgs),
                **( {"input_tokens":  in_tok}  if in_tok  is not None else {} ),
                **( {"output_tokens": out_tok} if out_tok is not None else {} ),
            },
            cost=LLMCost(
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost_usd,
            ) if (in_tok or out_tok) else None,
        ))

        # ── One tool node per tool_use block ──────────────────────────
        for block in tool_use_blocks:
            tname = block.get("name", "tool")
            tool_counters[tname] = tool_counters.get(tname, 0) + 1
            n = tool_counters[tname]
            tid = f"tool-{tname}" if n == 1 else f"tool-{tname}-{n}"
            ev = tool_end_by_id.get(block.get("id", ""), {})
            latency_ms = ev.get("latency_ms")
            _append(RunNode(
                id=tid,
                type=NodeType.TOOL,
                label=tname,
                metadata={
                    "tool": tname,
                    **( {"tool_input_hash":  _hash_dict(block.get("input", {}))} if block.get("input") else {} ),
                    **( {"result_truncated": ev["tool_response"][:200]}           if ev.get("tool_response")  else {} ),
                },
                cost=ToolCost(latency_ms=latency_ms) if latency_ms else None,
            ))

    # ── Build RunCapture and save ─────────────────────────────────────
    cap = RunCapture(
        test_case_id=test_case_id,
        store=store,
        path_id=_path_id_from_session(session),
        description=description,
    )
    for node in nodes.values():
        cap.add_node(node)
    cap._edges = edges
    cap._sequence = sequence
    cap._started_at = datetime.fromisoformat(session["started_at"])

    outcome = "success" if last_stop_reason == "end_turn" else last_stop_reason
    cap.finish(outcome=outcome)

    _session_path(session_id).unlink(missing_ok=True)


# ── Internal helpers ──────────────────────────────────────────────────

def _llm_label(seq: int, has_tool_use: bool) -> str:
    if seq == 1:
        return "Initial Analysis"
    return "Plan & Act" if has_tool_use else "Final Response"


def _hash_dict(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


def _path_id_from_session(session: dict) -> str:
    try:
        dt = datetime.fromisoformat(session["started_at"])
        return f"run-{dt.strftime('%Y%m%d-%H%M%S')}"
    except (KeyError, ValueError):
        return f"run-{session.get('session_id', 'unknown')[:8]}"
