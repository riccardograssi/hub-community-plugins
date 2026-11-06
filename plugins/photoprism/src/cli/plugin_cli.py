#!/usr/bin/env python3
"""CLI for this plugin REST API."""

import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("PLUGIN_API_BASE", "http://127.0.0.1:8080").rstrip("/")
HEALTH = os.environ.get("PLUGIN_HEALTH_PATH", "/health")


def get(path):
    request = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print("plugin-cli health")
        print("plugin-cli get <path>")
        return 0
    if argv[1] == "health":
        status, body = get(HEALTH)
        print(status)
        print(body)
        return 0 if status < 400 else 1
    if argv[1] == "get" and len(argv) == 3:
        path = argv[2] if argv[2].startswith("/") else "/" + argv[2]
        status, body = get(path)
        print(body)
        return 0 if status < 400 else 1
    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
