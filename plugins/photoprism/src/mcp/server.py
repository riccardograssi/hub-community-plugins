#!/usr/bin/env python3
"""MCP server on stdio. Tools call this plugin REST API."""

import json
import os
import sys
import urllib.error
import urllib.request

NAME = os.environ.get("PLUGIN_NAME", "plugin")
BASE = os.environ.get("PLUGIN_API_BASE", "http://127.0.0.1:8080").rstrip("/")
HEALTH = os.environ.get("PLUGIN_HEALTH_PATH", "/health")


def http_get(path):
    request = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", "replace")
            return {"status": response.status, "body": body[:4000]}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {"status": exc.code, "body": body[:4000]}


def tools():
    return [
        {
            "name": "health",
            "description": "GET %s on the %s REST API" % (HEALTH, NAME),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get",
            "description": "GET a path on the %s REST API" % NAME,
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    ]


def call_tool(name, arguments):
    if name == "health":
        return http_get(HEALTH)
    if name == "get":
        path = str((arguments or {}).get("path") or "/")
        if not path.startswith("/"):
            path = "/" + path
        return http_get(path)
    raise ValueError("unknown tool")


def send(message):
    raw = json.dumps(message).encode()
    header = ("Content-Length: %s\r\n\r\n" % len(raw)).encode()
    sys.stdout.buffer.write(header + raw)
    sys.stdout.buffer.flush()


def reply(message_id, result=None, error=None):
    if error is not None:
        send({"jsonrpc": "2.0", "id": message_id, "error": error})
    else:
        send({"jsonrpc": "2.0", "id": message_id, "result": result})


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode().partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode())


def handle(message):
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        reply(message_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": NAME, "version": "0.1.0"},
        })
        return
    if method == "notifications/initialized":
        return
    if method == "tools/list":
        reply(message_id, {"tools": tools()})
        return
    if method == "tools/call":
        try:
            data = call_tool(params.get("name"), params.get("arguments") or {})
        except (ValueError, urllib.error.URLError, TimeoutError) as exc:
            reply(message_id, error={"code": -32000, "message": str(exc)})
            return
        reply(message_id, {"content": [{"type": "text", "text": json.dumps(data)}]})
        return
    if message_id is not None:
        reply(message_id, error={"code": -32601, "message": "method not found"})


def main():
    while True:
        message = read_message()
        if message is None:
            return 0
        handle(message)


if __name__ == "__main__":
    raise SystemExit(main())
