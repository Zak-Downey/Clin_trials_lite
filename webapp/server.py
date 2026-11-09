"""The server factory: database path and registry functions in, a server out."""

from __future__ import annotations

import json
import mimetypes
import pathlib
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import storage

from .errors import ApiError, not_found
from .routes import COMPILED

STATIC = pathlib.Path(__file__).parent / "static"


class Context:
    """What handlers share: one connection, guarded by one lock, and the registry.

    The dispatcher holds the lock around every handler.
    """

    def __init__(self, db_path: str, fetch, find, find_page=None):
        # Used from request threads, under self.lock (taken by the dispatcher).
        self.conn = storage.connect(db_path, check_same_thread=False)
        self.lock = threading.RLock()
        self.fetch = fetch
        self.find = find
        self.find_page = find_page


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def _send(self, status: int, payload: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: int, body: dict):
        self._send(status, json.dumps(body).encode(), "application/json; charset=utf-8")

    def _static(self, path: str):
        name = "index.html" if path in ("", "/") else path[len("/static/"):] if path.startswith("/static/") else None
        target = (STATIC / name).resolve() if name else None
        if target is None or STATIC.resolve() not in target.parents and target != STATIC.resolve() or not target.is_file():
            return self._json(404, not_found().body())
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind == "application/javascript":
            kind += "; charset=utf-8"
        self._send(200, target.read_bytes(), kind)

    def _allowed_hosts(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}

    def _guard_origin(self, method: str):
        """Only this page may talk to this server: refuse a foreign Host (DNS rebinding)
        and, on writes, a foreign Origin."""
        allowed = self._allowed_hosts()
        if self.headers.get("Host") not in allowed:
            raise ApiError(403, "forbidden_host", "This server only answers requests addressed to it locally.")
        origin = self.headers.get("Origin")
        if method != "GET" and origin is not None and origin.removeprefix("http://") not in allowed:
            raise ApiError(403, "forbidden_origin", "This server only accepts writes from its own page.")

    def _is_json(self) -> bool:
        return self.headers.get_content_type() == "application/json"

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            raise ApiError(400, "invalid_json", "The request body is not valid JSON.")

    def _dispatch(self, method: str):
        path = urlsplit(self.path).path
        try:
            self._guard_origin(method)
            known_path = False
            for route_method, pattern, handler in COMPILED:
                match = pattern.match(path)
                if not match:
                    continue
                known_path = True
                if route_method != method:
                    continue
                if method == "POST" and not self._is_json():
                    raise ApiError(415, "unsupported_content_type", "Writes must be sent as application/json.")
                # One lock for every handler: the connection is shared, and a handler
                # cannot forget it. Handlers must not hold it across registry calls.
                body = self._body() if method == "POST" else None
                with self.server.ctx.lock:
                    result = handler(
                        self.server.ctx, query=parse_qs(urlsplit(self.path).query), body=body,
                        **match.groupdict(),
                    )
                return self._json(200, result)
            if known_path:
                raise ApiError(405, "method_not_allowed", f"{method} is not allowed here.")
            if method == "GET" and not path.startswith("/api/"):
                return self._static(path)
            raise not_found()
        except ApiError as err:
            self._json(err.status, err.body())
        except sqlite3.Error as err:
            self._json(500, ApiError(500, "database_error", f"The database failed: {err}").body())
        except Exception as err:  # never leak a traceback page
            self._json(500, ApiError(500, "server_error", f"Something went wrong: {err}").body())

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def make_server(db_path: str, fetch=None, find=None, find_page=None, host: str = "127.0.0.1", port: int = 0):
    """A server over `db_path` using the given registry functions (None until an endpoint needs them: no registry call is made without one)."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("The server only binds to the local machine.")
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.ctx = Context(db_path, fetch, find, find_page)
    return server
