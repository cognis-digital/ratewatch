"""ratewatch MCP server.

Exposes the macro/rates queries as MCP tools over stdio using newline-delimited
JSON-RPC 2.0. Standard library only — no SDK required — so it runs anywhere
Python does and can be wired into Cognis.Studio, Claude Desktop, or Cursor:

    {"command": "python", "args": ["-m", "ratewatch", "mcp"]}

Implemented methods:
  * initialize   — handshake, advertises the tools capability
  * tools/list   — describes the `yields`, `series`, and `calendar` tools
  * tools/call   — runs a tool and returns the result as JSON text
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from ratewatch import TOOL_NAME, TOOL_VERSION
from ratewatch.core import (
    RateWatchError,
    fetch_series,
    fetch_yield_curve,
    upcoming_events,
)

PROTOCOL_VERSION = "2024-11-05"

_TOOLS = [
    {
        "name": "yields",
        "description": "Return the latest US Treasury par-yield curve "
                       "(tenor -> percent) plus the 2s10s spread. Public "
                       "Treasury data; no API key required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offline": {"type": "boolean",
                            "description": "Use bundled sample data instead of the network."},
                "year": {"type": "integer",
                         "description": "Calendar year of the curve (default: current)."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "series",
        "description": "Return a FRED economic time series such as FEDFUNDS or "
                       "CPIAUCSL. Uses the free FRED_API_KEY env var when set; "
                       "otherwise degrades to bundled sample data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "series_id": {"type": "string",
                              "description": "FRED series id, e.g. FEDFUNDS, CPIAUCSL."},
                "limit": {"type": "integer",
                          "description": "Max observations to fetch live (default 24)."},
                "offline": {"type": "boolean",
                            "description": "Force bundled sample data."},
            },
            "required": ["series_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "calendar",
        "description": "Return upcoming FOMC / CPI / NFP and other macro "
                       "econ-calendar events from the bundled calendar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string",
                             "description": "Filter, e.g. FOMC, CPI, NFP, GDP."},
                "limit": {"type": "integer",
                          "description": "Max events to return."},
            },
            "additionalProperties": False,
        },
    },
]


def _result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "yields":
        curve = fetch_yield_curve(
            offline=bool(arguments.get("offline", False)),
            year=arguments.get("year"),
        )
        payload = curve.to_dict()
    elif name == "series":
        series_id = arguments.get("series_id")
        if not isinstance(series_id, str) or not series_id:
            raise ValueError("`series_id` (string) is required")
        series = fetch_series(
            series_id,
            limit=int(arguments.get("limit", 24)),
            offline=bool(arguments.get("offline", False)),
        )
        payload = series.to_dict()
    elif name == "calendar":
        events = upcoming_events(
            category=arguments.get("category"),
            limit=arguments.get("limit"),
        )
        payload = {"type": "calendar", "count": len(events),
                   "events": [e.to_dict() for e in events]}
    else:
        raise ValueError(f"unknown tool: {name}")

    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "isError": False,
    }


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Dispatch a single JSON-RPC request. Returns None for notifications."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    is_notification = "id" not in req

    if method == "initialize":
        res = _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": TOOL_NAME, "version": TOOL_VERSION},
        })
        return None if is_notification else res

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "ping":
        return None if is_notification else _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            return _result(req_id, _call_tool(name, arguments))
        except (ValueError, OSError, RateWatchError) as exc:
            return _error(req_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            return _error(req_id, -32603, f"internal error: {exc}")

    if is_notification:
        return None
    return _error(req_id, -32601, f"method not found: {method}")


def run_mcp_server(stdin=None, stdout=None) -> None:
    """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        response = handle_request(req)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
