"""Tests for the --format html report and the FRED series presets.

Standard library only; runs entirely offline over bundled sample data.
"""

import io
import os
import sys
import unittest
import xml.dom.minidom
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ratewatch.cli import (
    main,
    _render_series_html,
    _render_yields_html,
    _render_calendar_html,
)
from ratewatch.core import (
    SERIES_PRESETS,
    Series,
    bundled_series_ids,
    fetch_series,
    fetch_yield_curve,
    load_sample_series,
    preset_label,
    upcoming_events,
)

NEW_PRESETS = ("DGS2", "DGS10", "T10Y2Y", "UNRATE", "PCEPILFE")


def _well_formed_html(doc: str) -> None:
    """Assert the doc is parseable XML (a strict superset check for our markup)."""
    # Strip the doctype, then parse the single <html> root as XML.
    body = doc.split("\n", 1)[1] if doc.startswith("<!DOCTYPE") else doc
    xml.dom.minidom.parseString(body)


class TestPresets(unittest.TestCase):
    def test_all_new_presets_have_labels(self):
        for sid in NEW_PRESETS:
            self.assertIn(sid, SERIES_PRESETS)
            self.assertTrue(SERIES_PRESETS[sid])
            self.assertEqual(preset_label(sid), SERIES_PRESETS[sid])

    def test_preset_label_case_insensitive(self):
        self.assertEqual(preset_label("dgs10"), SERIES_PRESETS["DGS10"])

    def test_preset_label_unknown_empty(self):
        self.assertEqual(preset_label("NOT_A_SERIES"), "")

    def test_new_presets_are_bundled(self):
        bundled = {s.upper() for s in bundled_series_ids()}
        for sid in NEW_PRESETS:
            self.assertIn(sid, bundled)

    def test_bundled_sample_loads_with_title(self):
        for sid in NEW_PRESETS:
            s = load_sample_series(sid)
            self.assertTrue(s.observations)
            self.assertTrue(s.title)  # title resolves (file or preset fallback)

    def test_offline_fetch_each_preset(self):
        for sid in NEW_PRESETS:
            s = fetch_series(sid, api_key=None, offline=True)
            self.assertEqual(s.source, "fred-sample")
            self.assertTrue(s.observations)


class TestSeriesHtml(unittest.TestCase):
    def test_html_well_formed_and_content(self):
        s = load_sample_series("DGS10")
        doc = _render_series_html(s)
        self.assertTrue(doc.startswith("<!DOCTYPE html>"))
        _well_formed_html(doc)
        self.assertIn("DGS10", doc)
        self.assertIn(SERIES_PRESETS["DGS10"], doc)
        # Latest value highlighted exactly once (no duplicate row bug).
        self.assertEqual(doc.count('class="latest"'), 1)

    def test_html_row_count_matches_observations(self):
        s = load_sample_series("UNRATE")
        doc = _render_series_html(s)
        # one <tr> per observation in tbody, plus the header row.
        self.assertEqual(doc.count("<tr"), len(s.observations) + 1)

    def test_html_escapes_dynamic_text(self):
        s = Series(
            series_id="X<>&",
            observations=[{"date": "2026-01-01", "value": 1.0}],
            source="test",
            title="A & B <c>",
        )
        doc = _render_series_html(s)
        self.assertNotIn("<c>", doc)
        self.assertIn("&amp;", doc)
        _well_formed_html(doc)

    def test_html_handles_missing_value(self):
        s = Series(
            series_id="M",
            observations=[{"date": "2026-01-01", "value": None}],
            source="test",
            title="Missing",
        )
        doc = _render_series_html(s)
        _well_formed_html(doc)
        self.assertIn(">.<", doc.replace(" ", ""))


class TestYieldsAndCalendarHtml(unittest.TestCase):
    def test_yields_html(self):
        curve = fetch_yield_curve(offline=True)
        doc = _render_yields_html(curve)
        _well_formed_html(doc)
        self.assertIn("Yield Curve", doc)
        self.assertIn("10 Yr", doc)

    def test_calendar_html(self):
        import datetime
        events = upcoming_events(today=datetime.date(2026, 1, 1), limit=3)
        doc = _render_calendar_html(events)
        _well_formed_html(doc)
        self.assertIn("calendar", doc.lower())

    def test_calendar_html_empty(self):
        import datetime
        events = upcoming_events(today=datetime.date(2099, 1, 1))
        doc = _render_calendar_html(events)
        _well_formed_html(doc)
        self.assertIn("No upcoming events", doc)


class TestCliHtml(unittest.TestCase):
    def _capture(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_cli_series_html_each_preset(self):
        for sid in NEW_PRESETS:
            rc, out = self._capture(["series", sid, "--offline", "--format", "html"])
            self.assertEqual(rc, 0, sid)
            self.assertTrue(out.startswith("<!DOCTYPE html>"), sid)
            _well_formed_html(out)

    def test_cli_yields_html(self):
        rc, out = self._capture(["yields", "--offline", "--format", "html"])
        self.assertEqual(rc, 0)
        self.assertIn("<table", out)

    def test_cli_calendar_html(self):
        rc, out = self._capture(["calendar", "--format", "html"])
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("<!DOCTYPE html>"))

    def test_cli_html_to_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "report.html")
            rc = main(["series", "PCEPILFE", "--offline", "--format", "html",
                       "--out", path])
            self.assertEqual(rc, 0)
            with open(path, "r", encoding="utf-8") as fh:
                doc = fh.read()
            _well_formed_html(doc)
            self.assertIn("PCEPILFE", doc)


if __name__ == "__main__":
    unittest.main()
