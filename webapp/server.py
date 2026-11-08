"""The server factory: database path and registry functions in, a server out."""

from __future__ import annotations

import json
import mimetypes
import pathlib
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import storage

from .errors import ApiError, not_found
from .routes import COMPILED

STATIC = pathlib.Path(__file__).parent / "static"


class Context:
    """What handlers share: one connection, guarded by one lock, and the registry."""

    def __init__(self, db_path: str, fetch, find):
        # Used from request threads, always under self.lock.
        self.conn = storage.connect(db_path, check_same_thread=False)
        self.lock = threading.RLock()
        self.fetch = fetch
        self.find = find


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

    def _dispatch(self, method: str):
        path = urlsplit(self.path).path
        try:
            known_path = False
            for route_method, pattern, handler in COMPILED:
                match = pattern.match(path)
                if not match:
                    continue
                known_path = True
                if route_method != method:
                    continue
                return self._json(200, handler(self.server.ctx, **match.groupdict()))
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


def make_server(db_path: str, fetch=None, find=None, host: str = "127.0.0.1", port: int = 0):
    """A server over `db_path` using the given registry functions (real ones by default)."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("The server only binds to the local machine.")
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.ctx = Context(db_path, fetch, find)
    return server
