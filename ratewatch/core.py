"""Core engine for ratewatch — macro & rates data from public sources.

Two public data domains, both standard-library only (urllib):

  * Treasury  — the US Treasury Daily Par Yield Curve, served as public XML
                (no API key). We parse the Atom/XML feed into a curve of
                tenor -> percent yield.
  * FRED      — the St. Louis Fed FRED time-series API. Needs a *free* API key
                supplied via the ``FRED_API_KEY`` environment variable. When no
                key is present we degrade gracefully to bundled sample data so
                the tool is fully usable offline.

Plus a bundled economic calendar (JSON) of upcoming FOMC / CPI / NFP dates so
``ratewatch calendar`` works with zero network access.

No third-party dependencies. No network calls happen at import time; callers
opt in by passing ``offline=False``.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Tool identity (re-exported from the package __init__).
TOOL_NAME = "ratewatch"
TOOL_VERSION = "0.1.0"

# Where bundled sample/offline data lives.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Public endpoints (no key required for Treasury; FRED needs a free key).
TREASURY_XML_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/pages/xml"
)
FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"

# Friendly labels for commonly-watched FRED series. Used to provide a human
# title (and offline degrade hints) when the live API metadata is unavailable.
SERIES_PRESETS: Dict[str, str] = {
    "FEDFUNDS": "Federal Funds Effective Rate",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers: All Items",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "T10Y2Y": "10-Year minus 2-Year Treasury Spread",
    "UNRATE": "Unemployment Rate",
    "PCEPILFE": "Core PCE Price Index (excl. food & energy)",
}


def preset_label(series_id: str) -> str:
    """Friendly label for a known FRED series id, or '' if unknown."""
    return SERIES_PRESETS.get(series_id.upper(), "")

# Treasury par-yield tenors, in canonical curve order.
TREASURY_TENORS = (
    "1 Mo", "1.5 Month", "2 Mo", "3 Mo", "4 Mo", "6 Mo",
    "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr",
)

# Map the Treasury XML element local-names to display tenors.
_TREASURY_FIELD_MAP = {
    "BC_1MONTH": "1 Mo",
    "BC_1_5MONTH": "1.5 Month",
    "BC_2MONTH": "2 Mo",
    "BC_3MONTH": "3 Mo",
    "BC_4MONTH": "4 Mo",
    "BC_6MONTH": "6 Mo",
    "BC_1YEAR": "1 Yr",
    "BC_2YEAR": "2 Yr",
    "BC_3YEAR": "3 Yr",
    "BC_5YEAR": "5 Yr",
    "BC_7YEAR": "7 Yr",
    "BC_10YEAR": "10 Yr",
    "BC_20YEAR": "20 Yr",
    "BC_30YEAR": "30 Yr",
}

_HTTP_TIMEOUT = 15  # seconds
_USER_AGENT = f"{TOOL_NAME}/{TOOL_VERSION} (+https://cognis.digital)"


class RateWatchError(Exception):
    """Raised on unrecoverable data / parse / network problems."""


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class YieldCurve:
    """A single day's Treasury par-yield curve."""

    date: str  # ISO date, e.g. "2026-06-10"
    points: Dict[str, float] = field(default_factory=dict)  # tenor -> percent
    source: str = "treasury"

    def ordered(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for tenor in TREASURY_TENORS:
            if tenor in self.points:
                out.append({"tenor": tenor, "yield_pct": self.points[tenor]})
        return out

    def spread_2s10s_bps(self) -> Optional[float]:
        if "2 Yr" in self.points and "10 Yr" in self.points:
            return round((self.points["10 Yr"] - self.points["2 Yr"]) * 100, 1)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "yield_curve",
            "date": self.date,
            "source": self.source,
            "points": self.ordered(),
            "spread_2s10s_bps": self.spread_2s10s_bps(),
        }


@dataclass
class Series:
    """A FRED-style economic time series."""

    series_id: str
    observations: List[Dict[str, Any]] = field(default_factory=list)  # date,value
    source: str = "fred"
    units: str = ""
    title: str = ""

    def latest(self) -> Optional[Dict[str, Any]]:
        return self.observations[-1] if self.observations else None

    def to_dict(self) -> Dict[str, Any]:
        latest = self.latest()
        return {
            "type": "series",
            "series_id": self.series_id,
            "source": self.source,
            "title": self.title,
            "units": self.units,
            "count": len(self.observations),
            "latest": latest,
            "observations": self.observations,
        }


@dataclass
class CalendarEvent:
    """An upcoming macro / econ-calendar event."""

    date: str       # ISO date
    name: str       # e.g. "FOMC Rate Decision"
    category: str   # FOMC | CPI | NFP | GDP | ...
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "name": self.name,
            "category": self.category,
            "note": self.note,
        }


# --------------------------------------------------------------------------- #
# HTTP helper
# --------------------------------------------------------------------------- #
def _http_get(url: str, params: Optional[Dict[str, str]] = None) -> bytes:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        raise RateWatchError(f"network error fetching {url}: {exc}") from exc


# --------------------------------------------------------------------------- #
# Treasury yield curve
# --------------------------------------------------------------------------- #
def _local_name(tag: str) -> str:
    """Strip the XML namespace from an element tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_treasury_xml(xml_bytes: bytes) -> List[YieldCurve]:
    """Parse the Treasury par-yield Atom/XML feed into yield curves.

    The feed nests yield fields inside ``entry/content/properties``. We walk
    namespace-agnostically (matching by local element name) so the parser is
    resilient to namespace-URI changes.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise RateWatchError(f"could not parse Treasury XML: {exc}") from exc

    curves: List[YieldCurve] = []
    for el in root.iter():
        if _local_name(el.tag) != "properties":
            continue
        date_iso = ""
        points: Dict[str, float] = {}
        for child in el:
            name = _local_name(child.tag)
            text = (child.text or "").strip()
            if name == "NEW_DATE":
                # Treasury date may be "2026-06-10T00:00:00".
                date_iso = text.split("T", 1)[0]
            elif name in _TREASURY_FIELD_MAP and text:
                try:
                    points[_TREASURY_FIELD_MAP[name]] = float(text)
                except ValueError:
                    continue
        if date_iso and points:
            curves.append(YieldCurve(date=date_iso, points=points))
    curves.sort(key=lambda c: c.date)
    return curves


def _sample_treasury_path() -> str:
    return os.path.join(_DATA_DIR, "sample_treasury.xml")


def load_sample_yield_curve() -> YieldCurve:
    """Load the latest curve from bundled sample Treasury XML (offline)."""
    with open(_sample_treasury_path(), "rb") as fh:
        curves = parse_treasury_xml(fh.read())
    if not curves:
        raise RateWatchError("bundled sample Treasury data is empty")
    return curves[-1]


def fetch_yield_curve(offline: bool = False,
                      year: Optional[int] = None) -> YieldCurve:
    """Return the most recent Treasury par-yield curve.

    With ``offline=True`` (or on any network failure) returns the bundled
    sample curve so the tool always produces output.
    """
    if offline:
        return load_sample_yield_curve()
    year = year or _dt.date.today().year
    params = {
        "data": "daily_treasury_yield_curve",
        "field_tdr_date_value": str(year),
    }
    try:
        raw = _http_get(TREASURY_XML_URL, params)
        curves = parse_treasury_xml(raw)
        if not curves:
            raise RateWatchError("Treasury feed returned no curve data")
        return curves[-1]
    except RateWatchError:
        # Graceful degrade to bundled sample.
        curve = load_sample_yield_curve()
        curve.source = "treasury-sample (network unavailable)"
        return curve


# --------------------------------------------------------------------------- #
# FRED series
# --------------------------------------------------------------------------- #
def _sample_series_path(series_id: str) -> str:
    return os.path.join(_DATA_DIR, f"sample_{series_id.upper()}.json")


def load_sample_series(series_id: str) -> Series:
    """Load a bundled sample FRED series (offline / no key)."""
    path = _sample_series_path(series_id)
    if not os.path.exists(path):
        # Fall back to a generic bundled catalogue file if present.
        raise RateWatchError(
            f"no bundled sample for series '{series_id}'. "
            f"Set FRED_API_KEY to fetch it live, or try one of: "
            f"{', '.join(bundled_series_ids()) or '(none)'}"
        )
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Series(
        series_id=series_id.upper(),
        observations=data.get("observations", []),
        source="fred-sample",
        units=data.get("units", ""),
        title=data.get("title", "") or preset_label(series_id),
    )


def bundled_series_ids() -> List[str]:
    out: List[str] = []
    if os.path.isdir(_DATA_DIR):
        for fn in sorted(os.listdir(_DATA_DIR)):
            if fn.startswith("sample_") and fn.endswith(".json"):
                sid = fn[len("sample_"):-len(".json")]
                if sid.upper() not in ("CALENDAR",):
                    out.append(sid)
    return out


def parse_fred_json(series_id: str, payload: Dict[str, Any]) -> Series:
    obs: List[Dict[str, Any]] = []
    for o in payload.get("observations", []):
        val = o.get("value")
        # FRED uses "." for missing values.
        num: Optional[float]
        try:
            num = float(val) if val not in (".", "", None) else None
        except (TypeError, ValueError):
            num = None
        obs.append({"date": o.get("date", ""), "value": num})
    return Series(
        series_id=series_id.upper(),
        observations=obs,
        source="fred",
        title=preset_label(series_id),
    )


def fetch_series(series_id: str,
                 api_key: Optional[str] = None,
                 limit: int = 24,
                 offline: bool = False) -> Series:
    """Fetch a FRED time series, or degrade to bundled sample.

    Resolution order:
      1. offline=True              -> bundled sample
      2. no api_key (env unset)    -> bundled sample
      3. live fetch; on failure    -> bundled sample (if available) else raise
    """
    api_key = api_key if api_key is not None else os.environ.get("FRED_API_KEY")
    if offline or not api_key:
        return load_sample_series(series_id)

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": str(max(1, limit)),
    }
    try:
        raw = _http_get(FRED_OBS_URL, params)
        payload = json.loads(raw.decode("utf-8"))
        series = parse_fred_json(series_id, payload)
        # We asked desc; present ascending.
        series.observations.reverse()
        return series
    except (RateWatchError, json.JSONDecodeError):
        if os.path.exists(_sample_series_path(series_id)):
            s = load_sample_series(series_id)
            s.source = "fred-sample (live fetch unavailable)"
            return s
        raise


# --------------------------------------------------------------------------- #
# Economic calendar
# --------------------------------------------------------------------------- #
def _calendar_path() -> str:
    return os.path.join(_DATA_DIR, "calendar.json")


def load_calendar() -> List[CalendarEvent]:
    with open(_calendar_path(), "r", encoding="utf-8") as fh:
        data = json.load(fh)
    events: List[CalendarEvent] = []
    for e in data.get("events", []):
        events.append(CalendarEvent(
            date=e.get("date", ""),
            name=e.get("name", ""),
            category=e.get("category", ""),
            note=e.get("note", ""),
        ))
    events.sort(key=lambda ev: ev.date)
    return events


def upcoming_events(today: Optional[_dt.date] = None,
                    category: Optional[str] = None,
                    limit: Optional[int] = None) -> List[CalendarEvent]:
    """Return calendar events on/after ``today``, optionally filtered."""
    today = today or _dt.date.today()
    today_iso = today.isoformat()
    events = [e for e in load_calendar() if e.date >= today_iso]
    if category:
        cat = category.upper()
        events = [e for e in events if e.category.upper() == cat]
    if limit is not None:
        events = events[:limit]
    return events
