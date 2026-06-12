"""ratewatch — macro & rates CLI. Part of the Cognis Neural Suite."""

from ratewatch.core import (
    TOOL_NAME,
    TOOL_VERSION,
    RateWatchError,
    YieldCurve,
    Series,
    CalendarEvent,
    fetch_yield_curve,
    fetch_series,
    load_calendar,
    upcoming_events,
    load_sample_yield_curve,
    load_sample_series,
    bundled_series_ids,
    parse_treasury_xml,
    parse_fred_json,
    SERIES_PRESETS,
    preset_label,
)

__version__ = TOOL_VERSION

__all__ = [
    "TOOL_NAME",
    "TOOL_VERSION",
    "__version__",
    "RateWatchError",
    "YieldCurve",
    "Series",
    "CalendarEvent",
    "fetch_yield_curve",
    "fetch_series",
    "load_calendar",
    "upcoming_events",
    "load_sample_yield_curve",
    "load_sample_series",
    "bundled_series_ids",
    "parse_treasury_xml",
    "parse_fred_json",
    "SERIES_PRESETS",
    "preset_label",
]
