"""Deep tests for ratewatch — parsing, degradation, MCP protocol."""

import datetime
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ratewatch.core import (
    RateWatchError,
    fetch_series,
    fetch_yield_curve,
    load_sample_series,
    load_sample_yield_curve,
    parse_fred_json,
    parse_treasury_xml,
    upcoming_events,
    bundled_series_ids,
)
from ratewatch import mcp_server


SAMPLE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
      xmlns="http://www.w3.org/2005/Atom">
  <entry><content><m:properties>
    <d:NEW_DATE>2026-01-02T00:00:00</d:NEW_DATE>
    <d:BC_2YEAR>3.50</d:BC_2YEAR>
    <d:BC_10YEAR>4.00</d:BC_10YEAR>
  </m:properties></content></entry>
  <entry><content><m:properties>
    <d:NEW_DATE>2026-01-03T00:00:00</d:NEW_DATE>
    <d:BC_2YEAR>3.60</d:BC_2YEAR>
    <d:BC_10YEAR>4.10</d:BC_10YEAR>
  </m:properties></content></entry>
</feed>"""


class TestTreasuryParsing(unittest.TestCase):
    def test_parse_namespace_agnostic(self):
        curves = parse_treasury_xml(SAMPLE_XML)
        self.assertEqual(len(curves), 2)
        # sorted ascending; last is most recent
        self.assertEqual(curves[-1].date, "2026-01-03")
        self.assertEqual(curves[-1].points["10 Yr"], 4.10)

    def test_spread_computation(self):
        curves = parse_treasury_xml(SAMPLE_XML)
        # 4.10 - 3.60 = 0.50 pct = 50 bps
        self.assertEqual(curves[-1].spread_2s10s_bps(), 50.0)

    def test_bad_xml_raises(self):
        with self.assertRaises(RateWatchError):
            parse_treasury_xml(b"<not valid")

    def test_bundled_sample_loads(self):
        curve = load_sample_yield_curve()
        self.assertTrue(curve.points)
        self.assertIn("10 Yr", curve.points)


class TestFredParsing(unittest.TestCase):
    def test_parse_handles_missing_dots(self):
        payload = {"observations": [
            {"date": "2026-01-01", "value": "4.33"},
            {"date": "2026-02-01", "value": "."},
        ]}
        s = parse_fred_json("FEDFUNDS", payload)
        self.assertEqual(s.observations[0]["value"], 4.33)
        self.assertIsNone(s.observations[1]["value"])

    def test_offline_degrade_no_key(self):
        # No api_key -> bundled sample regardless of network.
        s = fetch_series("FEDFUNDS", api_key=None, offline=False)
        self.assertEqual(s.source, "fred-sample")
        self.assertTrue(s.observations)
        self.assertEqual(s.latest()["date"], s.observations[-1]["date"])

    def test_unknown_series_raises(self):
        with self.assertRaises(RateWatchError):
            load_sample_series("DEFINITELY_NOT_BUNDLED")

    def test_bundled_ids_present(self):
        ids = [i.upper() for i in bundled_series_ids()]
        self.assertIn("FEDFUNDS", ids)
        self.assertIn("CPIAUCSL", ids)


class TestYieldDegrade(unittest.TestCase):
    def test_offline_flag(self):
        curve = fetch_yield_curve(offline=True)
        self.assertTrue(curve.points)


class TestCalendar(unittest.TestCase):
    def test_filter_and_future(self):
        # Use a fixed early date so the bundled events are all in the future.
        events = upcoming_events(today=datetime.date(2026, 1, 1))
        self.assertTrue(events)
        fomc = upcoming_events(today=datetime.date(2026, 1, 1), category="FOMC")
        self.assertTrue(all(e.category == "FOMC" for e in fomc))

    def test_far_future_empty(self):
        events = upcoming_events(today=datetime.date(2099, 1, 1))
        self.assertEqual(events, [])

    def test_limit(self):
        events = upcoming_events(today=datetime.date(2026, 1, 1), limit=3)
        self.assertLessEqual(len(events), 3)


class TestMcpProtocol(unittest.TestCase):
    def test_initialize_and_list(self):
        init = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init["result"]["serverInfo"]["name"], "ratewatch")

        lst = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in lst["result"]["tools"]}
        self.assertEqual(names, {"yields", "series", "calendar"})

    def test_tools_call_yields_offline(self):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "yields", "arguments": {"offline": True}},
        })
        self.assertFalse(resp["result"]["isError"])
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        self.assertEqual(data["type"], "yield_curve")

    def test_tools_call_series_requires_id(self):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "series", "arguments": {}},
        })
        self.assertIn("error", resp)

    def test_unknown_method(self):
        resp = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 5, "method": "bogus"})
        self.assertEqual(resp["error"]["code"], -32601)

    def test_run_loop_roundtrip(self):
        stdin = io.StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"tools/call",'
            '"params":{"name":"calendar","arguments":{"limit":2}}}\n')
        stdout = io.StringIO()
        mcp_server.run_mcp_server(stdin=stdin, stdout=stdout)
        out = json.loads(stdout.getvalue().strip())
        data = json.loads(out["result"]["content"][0]["text"])
        self.assertEqual(data["type"], "calendar")


if __name__ == "__main__":
    unittest.main()
