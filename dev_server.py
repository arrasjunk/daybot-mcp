#!/usr/bin/env python3
"""
Dev auto-port launcher for DayBot MCP.

Finds a free port starting from the desired port (default 8000) and launches the
FastAPI server with uvicorn. Useful when port 8000 is already in use.

Usage:
  python dev_server.py              # tries 8000, falls back to 8001, 8002, ...
  python dev_server.py --start-port 8001 --host 127.0.0.1 --max-tries 20

Respects environment variables if set:
  SERVER_HOST, SERVER_PORT
"""

import argparse
import os
import socket
import sys
from typing import Optional

import uvicorn


def is_port_free(host: str, port: int) -> bool:
    """Return True if the port is free to bind on given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(host: str, start_port: int, max_tries: int) -> Optional[int]:
    """Find a free port starting at start_port, trying up to max_tries sequentially."""
    for offset in range(max_tries):
        candidate = start_port + offset
        if is_port_free(host, candidate):
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(description="Dev auto-port launcher for DayBot MCP")
    parser.add_argument("--host", default=os.getenv("SERVER_HOST", "127.0.0.1"), help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--start-port", type=int, default=int(os.getenv("SERVER_PORT", 8000)), help="Starting port to try (default: 8000)")
    parser.add_argument("--max-tries", type=int, default=20, help="Max number of ports to try (default: 20)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for dev")

    args = parser.parse_args()

    port = find_free_port(args.host, args.start_port, args.max_tries)
    if port is None:
        print(f"ERROR: No free port found in range {args.start_port}-{args.start_port + args.max_tries - 1}")
        sys.exit(1)

    if port != args.start_port:
        print(f"Port {args.start_port} is in use. Launching on port {port} instead...")
    else:
        print(f"Launching on port {port} ...")

    uvicorn.run(
        "daybot_mcp.server:app",
        host=args.host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
