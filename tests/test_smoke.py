"""Smoke tests for ratewatch. Standard library only, no network."""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ratewatch import TOOL_NAME, TOOL_VERSION
from ratewatch.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(TOOL_NAME, "ratewatch")
        self.assertTrue(TOOL_VERSION)


class TestCliOffline(unittest.TestCase):
    def test_yields_offline_table(self):
        self.assertEqual(main(["yields", "--offline"]), 0)

    def test_yields_offline_json(self):
        self.assertEqual(main(["yields", "--offline", "--format", "json"]), 0)

    def test_series_offline(self):
        self.assertEqual(main(["series", "FEDFUNDS", "--offline"]), 0)
        self.assertEqual(main(["series", "CPIAUCSL", "--offline"]), 0)

    def test_series_unknown_offline_exits_2(self):
        self.assertEqual(main(["series", "NOPE_NOT_A_SERIES", "--offline"]), 2)

    def test_calendar(self):
        self.assertEqual(main(["calendar"]), 0)

    def test_no_command_exits_2(self):
        self.assertEqual(main([]), 2)


class TestSubprocess(unittest.TestCase):
    def _run(self, args):
        return subprocess.run(
            [sys.executable, "-m", "ratewatch"] + args,
            cwd=REPO_ROOT, capture_output=True, text=True,
        )

    def test_version(self):
        proc = self._run(["--version"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ratewatch", proc.stdout)

    def test_help(self):
        proc = self._run(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_yields_json_payload(self):
        proc = self._run(["yields", "--offline", "--format", "json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["type"], "yield_curve")
        tenors = {p["tenor"] for p in data["points"]}
        self.assertIn("10 Yr", tenors)
        self.assertIn("2 Yr", tenors)
        self.assertIsNotNone(data["spread_2s10s_bps"])


if __name__ == "__main__":
    unittest.main()
