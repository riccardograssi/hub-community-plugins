"""HTTP server for people groups. Stdlib only, so it runs in the PhotoPrism image."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import people_groups

UPSTREAM = os.environ.get("PHOTOPRISM_UPSTREAM", "http://photoprism:2342").rstrip("/")
_LOCK = threading.Lock()
_TOKEN = ""
_PREVIEW = "public"


def _login() -> None:
    global _TOKEN, _PREVIEW
    password = os.environ.get("PHOTOPRISM_ADMIN_PASSWORD", "")
    if not password:
        _TOKEN = ""
        _PREVIEW = "public"
        return
    user = os.environ.get("PHOTOPRISM_ADMIN_USER", "admin")
    payload = json.dumps({"username": user, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        UPSTREAM + "/api/v1/session",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    _TOKEN = str(data.get("id") or "")
    config = data.get("config") if isinstance(data, dict) else None
    preview = ""
    if isinstance(config, dict):
        preview = str(config.get("previewToken") or "")
    _PREVIEW = preview or "public"


def _auth_headers(refresh: bool) -> dict[str, str]:
    global _TOKEN
    with _LOCK:
        if refresh:
            _TOKEN = ""
        if not _TOKEN and os.environ.get("PHOTOPRISM_ADMIN_PASSWORD", ""):
            try:
                _login()
            except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
                _TOKEN = ""
        if not _TOKEN:
            return {}
        return {"X-Auth-Token": _TOKEN}


def fetch(path: str, params: dict[str, str] | None, refresh: bool = False) -> tuple[int, str, bytes]:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    headers = _auth_headers(refresh)
    request = urllib.request.Request(UPSTREAM + path + query, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            ctype = response.headers.get("Content-Type") or "application/octet-stream"
            return response.status, ctype, response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and not refresh:
            return fetch(path, params, refresh=True)
        return exc.code, "application/octet-stream", b""


def get_json(path: str, params: dict[str, str] | None) -> tuple[int, Any]:
    status, _ctype, raw = fetch(path, params)
    if status != 200 or not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return status, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def log_message(self, fmt: str, *args: Any) -> None:
        path = self.path.split("?", 1)[0]
        print(f"{self.command} {path}", flush=True)

    def _handle(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or "0")
        if length > 1_000_000:
            self._send(413, "application/json; charset=utf-8", b'{"error":"too_large"}')
            return
        body = self.rfile.read(length) if length else b""
        if parsed.path.rstrip("/") == "/__hub/people-groups/api/thumb":
            self._thumb(parsed.query)
            return
        status, content_type, payload = people_groups.dispatch(
            self.command, parsed.path, parsed.query, body, get_json
        )
        self._send(status, content_type, payload)

    def _thumb(self, query: str) -> None:
        params = urllib.parse.parse_qs(query)
        digest = (params.get("hash") or [""])[-1].strip()
        if not digest or "/" in digest or ".." in digest:
            self._send(400, "application/json; charset=utf-8", b'{"error":"hash"}')
            return
        _auth_headers(False)
        status, content_type, payload = fetch(
            f"/api/v1/t/{urllib.parse.quote(digest)}/{urllib.parse.quote(_PREVIEW)}/tile_224",
            None,
        )
        if status != 200 or not payload:
            self._send(404, "application/json; charset=utf-8", b'{"error":"thumb"}')
            return
        self._send(200, content_type.split(";")[0] or "image/jpeg", payload)

    def _send(self, status: int, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    listen = os.environ.get("GROUPS_LISTEN", "0.0.0.0:8095")
    host, _, port_text = listen.rpartition(":")
    server = ThreadingHTTPServer((host or "0.0.0.0", int(port_text)), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
