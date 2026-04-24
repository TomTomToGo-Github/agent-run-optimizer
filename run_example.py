"""
run_example.py — load a YAML run graph and open an interactive visualization.

Usage:
    python run_example.py [--test-case incident-resolution] [--port 8765]

Sync button in the UI writes node state (user_important toggles) back to the store.
Swap YAMLRunStore for any other RunStoreBase implementation — nothing else changes.
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent_run_optimizer.storage.base import RunStoreBase
from agent_run_optimizer.storage.yaml_store import YAMLRunStore
from agent_run_optimizer.viz.html import HtmlViz


def _find_free_port(start: int = 8765, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket() as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range %d–%d" % (start, start + attempts))


def _make_handler(html_content: str, store: RunStoreBase, test_case_id: str):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                body = html_content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/sync":
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
                try:
                    store.sync_node_states(payload["test_case_id"], payload["updates"])
                    result = {"status": "ok", "message": "Synced to store successfully"}
                except Exception as exc:
                    result = {"status": "error", "message": str(exc)}
                body = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
            pass  # suppress noisy access logs

    return _Handler


def serve_and_open(
    test_case_id: str,
    store: RunStoreBase,
    port: int | None = None,
) -> None:
    graph = store.load(test_case_id)
    html = HtmlViz().generate_html(graph)

    port = port or _find_free_port()
    handler = _make_handler(html, store, test_case_id)
    server = HTTPServer(("localhost", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{port}"
    print()
    print("  AI Run Graph Visualization")
    print(f"  Test case : {test_case_id}")
    print(f"  Store     : {store.__class__.__name__}")
    print()
    print(f"  Opening   {url}")
    print("  Press Ctrl-C to stop")
    print()

    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        print("\n  Server stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize a run graph from a YAML store.")
    parser.add_argument("--test-case", default="incident-resolution", help="Test case ID (YAML stem)")
    parser.add_argument("--runs-dir",  default="runs",                 help="Directory containing YAML run files")
    parser.add_argument("--port",      type=int, default=None,         help="Local port (auto-selected if omitted)")
    args = parser.parse_args()

    # ── Swap this line to use a different backend ──────────────────────
    store: RunStoreBase = YAMLRunStore(runs_dir=args.runs_dir)
    # e.g. store = PostgresRunStore(dsn=os.environ["DATABASE_URL"])
    # ──────────────────────────────────────────────────────────────────

    serve_and_open(test_case_id=args.test_case, store=store, port=args.port)


if __name__ == "__main__":
    main()