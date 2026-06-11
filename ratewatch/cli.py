"""Command-line interface for ratewatch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from ratewatch import TOOL_NAME, TOOL_VERSION
from ratewatch.core import (
    RateWatchError,
    Series,
    YieldCurve,
    bundled_series_ids,
    fetch_series,
    fetch_yield_curve,
    upcoming_events,
)


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
def _render_yields_table(curve: YieldCurve) -> str:
    lines: List[str] = []
    lines.append(f"US Treasury Par Yield Curve — {curve.date}  (source: {curve.source})")
    lines.append("=" * 56)
    lines.append(f"{'Tenor':<10} {'Yield %':>10}")
    lines.append("-" * 56)
    for pt in curve.ordered():
        lines.append(f"{pt['tenor']:<10} {pt['yield_pct']:>10.2f}")
    lines.append("-" * 56)
    spread = curve.spread_2s10s_bps()
    if spread is not None:
        shape = "inverted" if spread < 0 else "normal"
        lines.append(f"2s10s spread: {spread:+.1f} bps ({shape})")
    return "\n".join(lines)


def _render_series_table(series: Series) -> str:
    lines: List[str] = []
    title = series.title or series.series_id
    head = f"FRED series {series.series_id}"
    if series.title:
        head += f" — {series.title}"
    lines.append(f"{head}  (source: {series.source})")
    if series.units:
        lines.append(f"units: {series.units}")
    lines.append("=" * 56)
    lines.append(f"{'Date':<14} {'Value':>14}")
    lines.append("-" * 56)
    for o in series.observations:
        val = o.get("value")
        vs = f"{val:.4f}" if isinstance(val, (int, float)) else "."
        lines.append(f"{o.get('date', ''):<14} {vs:>14}")
    lines.append("-" * 56)
    latest = series.latest()
    if latest and isinstance(latest.get("value"), (int, float)):
        lines.append(f"latest: {latest['value']:.4f}  ({latest['date']})")
    lines.append(f"observations: {len(series.observations)}")
    return "\n".join(lines)


def _render_calendar_table(events: List[Any]) -> str:
    lines: List[str] = []
    lines.append("Upcoming macro / econ-calendar events")
    lines.append("=" * 64)
    if not events:
        lines.append("No upcoming events in the bundled calendar.")
        return "\n".join(lines)
    lines.append(f"{'Date':<12} {'Category':<8} {'Event'}")
    lines.append("-" * 64)
    for e in events:
        lines.append(f"{e.date:<12} {e.category:<8} {e.name}")
        if e.note:
            lines.append(f"{'':<21}{e.note}")
    lines.append("-" * 64)
    lines.append(f"{len(events)} event(s).")
    return "\n".join(lines)


def _emit(text: str, out: Optional[str]) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Macro & rates CLI — Fed funds, CPI, Treasury yields, and "
                    "key econ-calendar dates from public sources.",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command")

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--format", choices=("table", "json"), default="table",
                        help="Output format (default: table).")
        sp.add_argument("--out", help="Write output to this file instead of stdout.")
        sp.add_argument("--offline", action="store_true",
                        help="Use bundled sample data; no network calls.")

    y = sub.add_parser("yields", help="Show the US Treasury par-yield curve.")
    _common(y)
    y.add_argument("--year", type=int, default=None,
                   help="Calendar year of the curve to fetch (default: current).")

    s = sub.add_parser("series", help="Show a FRED time series (e.g. FEDFUNDS, CPIAUCSL).")
    s.add_argument("series_id", help="FRED series id, e.g. FEDFUNDS or CPIAUCSL.")
    s.add_argument("--limit", type=int, default=24,
                   help="Max observations to fetch live (default: 24).")
    _common(s)

    c = sub.add_parser("calendar", help="Upcoming FOMC / CPI / NFP dates (bundled).")
    c.add_argument("--category", default=None,
                   help="Filter by category (FOMC, CPI, NFP, GDP, ...).")
    c.add_argument("--limit", type=int, default=None,
                   help="Show at most N upcoming events.")
    c.add_argument("--format", choices=("table", "json"), default="table")
    c.add_argument("--out", help="Write output to this file instead of stdout.")

    sub.add_parser("mcp", help="Run as an MCP server (stdio JSON-RPC).")
    return p


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
def _run_yields(args: argparse.Namespace) -> int:
    try:
        curve = fetch_yield_curve(offline=args.offline, year=args.year)
    except RateWatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        _emit(json.dumps(curve.to_dict(), indent=2), args.out)
    else:
        _emit(_render_yields_table(curve), args.out)
    return 0


def _run_series(args: argparse.Namespace) -> int:
    try:
        series = fetch_series(args.series_id, limit=args.limit, offline=args.offline)
    except RateWatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        _emit(json.dumps(series.to_dict(), indent=2), args.out)
    else:
        _emit(_render_series_table(series), args.out)
    return 0


def _run_calendar(args: argparse.Namespace) -> int:
    try:
        events = upcoming_events(category=args.category, limit=args.limit)
    except (RateWatchError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        payload = {"type": "calendar", "count": len(events),
                   "events": [e.to_dict() for e in events]}
        _emit(json.dumps(payload, indent=2), args.out)
    else:
        _emit(_render_calendar_table(events), args.out)
    return 0


def _run_mcp() -> int:
    from ratewatch.mcp_server import run_mcp_server
    run_mcp_server()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "yields":
        return _run_yields(args)
    if args.command == "series":
        return _run_series(args)
    if args.command == "calendar":
        return _run_calendar(args)
    if args.command == "mcp":
        return _run_mcp()
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
