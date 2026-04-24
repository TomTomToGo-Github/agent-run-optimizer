"""
run_example.py — load a YAML run graph and open an interactive visualization.

Usage:
    python run_example.py [--test-case incident-resolution] [--port 8765]

Sync button in the UI writes node state back to the store.
The case dropdown in the UI lets you switch between all available test cases.
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
from urllib.parse import parse_qs, urlparse

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


def _make_handler(html_content: str, store: RunStoreBase, viz: HtmlViz):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)

            if parsed.path in ("/", "/index.html"):
                body = html_content.encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body)

            elif parsed.path == "/api/cases":
                self._send_json({"cases": sorted(store.list_test_cases())})

            elif parsed.path == "/api/graph":
                params   = parse_qs(parsed.query)
                tc_id    = (params.get("id") or [None])[0]
                if not tc_id:
                    self._send_json({"error": "Missing ?id= parameter"}, 400)
                    return
                try:
                    graph = store.load(tc_id)
                    self._send_json(viz.build_graph_data(graph))
                except FileNotFoundError:
                    self._send_json({"error": f"Test case not found: {tc_id}"}, 404)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 500)

            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/api/sync":
                length  = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
                try:
                    store.sync_node_states(payload["test_case_id"], payload["updates"])
                    self._send_json({"status": "ok", "message": "Synced to store successfully"})
                except Exception as exc:
                    self._send_json({"status": "error", "message": str(exc)})
            else:
                self.send_response(404)
                self.end_headers()

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, data: dict, status: int = 200) -> None:
            self._send(status, "application/json", json.dumps(data).encode("utf-8"))

        def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
            pass  # suppress noisy access logs

    return _Handler


def serve_and_open(
    store: RunStoreBase,
    port: int | None = None,
) -> None:
    viz   = HtmlViz()
    cases = store.list_test_cases()
    graph = store.load(cases[0])
    html  = viz.generate_html(graph, cases=cases)

    port    = port or _find_free_port()
    handler = _make_handler(html, store, viz)
    server  = HTTPServer(("localhost", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{port}"
    print()
    print("  AI Run Graph Visualization")
    print(f"  Cases     : {', '.join(sorted(cases))}")
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
    # parser.add_argument("--test-case", default="incident-resolution", help="Initial test case to display")
    parser.add_argument("--runs-dir",  default="agent_runs",          help="Root directory containing agent run folders")
    parser.add_argument("--port",      type=int, default=None,        help="Local port (auto-selected if omitted)")
    args = parser.parse_args()

    # ── Swap this line to use a different backend ──────────────────────
    store: RunStoreBase = YAMLRunStore(runs_dir=args.runs_dir)
    # e.g. store = PostgresRunStore(dsn=os.environ["DATABASE_URL"])
    # ──────────────────────────────────────────────────────────────────

    serve_and_open(store=store, port=args.port)


if __name__ == "__main__":
    main()
