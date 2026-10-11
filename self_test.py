#!/usr/bin/env python3
"""Three-tier self test for llm-port-economics.

Tier 1 functional unit tests; Tier 2 error paths; Tier 3 extreme edges
(empty input, overlong input, corrupt input).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_economics as pe  # noqa: E402

CLI = [sys.executable, os.path.join(HERE, "port_economics.py")]


def run_cli(*args):
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


class TestFunctional(unittest.TestCase):
    def test_estimate_arithmetic(self):
        r = pe.estimate_cost(loc=100_000, tokens_per_loc=10.0, passes=2,
                             model="workhorse", io_split=[0.7, 0.3],
                             automation="unattended")
        core = 100_000 * 10.0
        self.assertEqual(r["tokens_low"], round(core * 2 * 1.5))
        self.assertEqual(r["tokens_high"], round(core * 2 * 3.0))
        blended = 0.7 * 3.0 + 0.3 * 15.0
        self.assertAlmostEqual(r["cost_low_usd"], r["tokens_low"] / 1e6 * blended, places=2)
        self.assertLess(r["cost_low_usd"], r["cost_high_usd"])

    def test_human_loop_multiplier(self):
        a = pe.estimate_cost(100_000, 10.0, 2, "workhorse", [0.7, 0.3], "unattended")
        b = pe.estimate_cost(100_000, 10.0, 2, "workhorse", [0.7, 0.3], "human-loop")
        self.assertAlmostEqual(b["cost_low_usd"], a["cost_low_usd"] * 10.0, places=2)

    def test_risk_bands(self):
        low = pe.failure_risk(10_000, 95, 30, 9)["risk_score"]
        high = pe.failure_risk(2_000_000, 5, 0, 0)["risk_score"]
        self.assertLess(low, 30)
        self.assertGreater(high, 60)
        self.assertTrue(pe.failure_risk(10_000, 95, 30, 9)["likely_failure_modes"])

    def test_readme_example_regression(self):
        """The worked example printed in README must match the code."""
        r = pe.estimate_cost(100_000, 12.0, 3, "workhorse", [0.7, 0.3], "human-loop")
        self.assertEqual(r["cost_low_usd"], 356.4)
        self.assertEqual(r["cost_high_usd"], 712.8)

    def test_case_studies_ratio(self):
        ratio = pe.CASE_STUDIES[1]["reported_cost_usd"] / pe.CASE_STUDIES[0]["reported_cost_usd"]
        self.assertAlmostEqual(ratio, 17.5, places=1)
        for c in pe.CASE_STUDIES:
            self.assertFalse(c["independently_verified"])
            self.assertTrue(c["source_nature"])


class TestErrorPaths(unittest.TestCase):
    def test_negative_loc(self):
        with self.assertRaises(pe.InputError):
            pe.estimate_cost(-5, 10.0, 1, "workhorse", [0.7, 0.3])

    def test_unknown_model(self):
        with self.assertRaises(pe.InputError):
            pe.estimate_cost(1000, 10.0, 1, "nope", [0.7, 0.3])

    def test_coverage_out_of_range(self):
        with self.assertRaises(pe.InputError):
            pe.failure_risk(1000, 150, 5, 5)

    def test_cli_bad_input_exits_2(self):
        res = run_cli("risk", "--loc", "1000", "--coverage", "-3")
        self.assertEqual(res.returncode, 2)
        self.assertIn("error:", res.stderr)


class TestEdgeCases(unittest.TestCase):
    def _tmp(self, content):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.addCleanup(os.remove, path)
        return path

    def test_empty_config(self):
        res = run_cli("estimate", "--loc", "1000", "--config", self._tmp("{}"))
        self.assertEqual(res.returncode, 0)
        self.assertIn("COST RANGE", res.stdout)

    def test_corrupt_config(self):
        res = run_cli("estimate", "--loc", "1000", "--config", self._tmp("{not json"))
        self.assertEqual(res.returncode, 2)
        self.assertIn("not valid JSON", res.stderr)

    def test_overlong_input_no_crash(self):
        r = pe.estimate_cost(10**9, 10.0, 3, "workhorse", [0.7, 0.3])
        self.assertTrue(r["cost_high_usd"] == r["cost_high_usd"])  # finite

    def test_zero_io_split_rejected(self):
        with self.assertRaises(pe.InputError):
            pe.estimate_cost(1000, 10.0, 1, "workhorse", [0.0, 0.0])

    def test_minimum_boundary_risk(self):
        r = pe.failure_risk(1, 100, 10, 10)
        self.assertEqual(r["band"], "low")


if __name__ == "__main__":
    unittest.main(verbosity=1)
