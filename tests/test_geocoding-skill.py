#!/usr/bin/env python3
"""Tests for geocoding-skill: geocoding logic and rate limiting."""

import sys
import os
import json
import time
import tempfile
import argparse
import unittest
from unittest.mock import patch, MagicMock
import importlib.util

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "geocoding-skill.py")
spec = importlib.util.spec_from_file_location("geocoding_skill", SCRIPT_PATH)
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


class TestNominatimGeocode(unittest.TestCase):
    """Test Nominatim forward geocoding."""

    @patch("requests.get")
    def test_geocode_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{
            "lat": "39.9042",
            "lon": "116.4074",
            "display_name": "Beijing, China",
            "type": "city",
            "importance": 0.8,
            "osm_id": 12345,
        }]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = gc.nominatim_geocode("Beijing, China")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["lat"], 39.9042)
        self.assertAlmostEqual(result["lon"], 116.4074)
        self.assertEqual(result["provider"], "nominatim")

    @patch("requests.get")
    def test_geocode_no_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = gc.nominatim_geocode("NonexistentPlace12345")
        self.assertIsNone(result)

    @patch("requests.get")
    def test_geocode_network_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection error")
        result = gc.nominatim_geocode("Beijing")
        self.assertIsNone(result)


class TestNominatimReverse(unittest.TestCase):
    """Test Nominatim reverse geocoding."""

    @patch("requests.get")
    def test_reverse_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "lat": "39.9042",
            "lon": "116.4074",
            "display_name": "Beijing, China",
            "type": "city",
            "address": {"country": "China", "city": "Beijing"},
            "osm_id": 12345,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = gc.nominatim_reverse(39.9042, 116.4074)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["lat"], 39.9042)
        self.assertEqual(result["address"]["country"], "China")

    @patch("requests.get")
    def test_reverse_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "Unable to geocode"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = gc.nominatim_reverse(0, 0)
        self.assertIsNone(result)


class TestOpenMeteoGeocode(unittest.TestCase):
    """Test Open-Meteo geocoding."""

    @patch("requests.get")
    def test_openmeteo_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{
                "latitude": 35.6762,
                "longitude": 139.6503,
                "name": "Tokyo",
                "country": "Japan",
                "admin1": "Tokyo",
                "timezone": "Asia/Tokyo",
            }]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = gc.openmeteo_geocode("Tokyo")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["lat"], 35.6762)
        self.assertEqual(result["name"], "Tokyo")
        self.assertEqual(result["provider"], "open-meteo")


class TestRateLimiting(unittest.TestCase):
    """Test rate limiting behavior."""

    def test_rate_limit_constant(self):
        self.assertEqual(gc.NOMINATIM_RATE_LIMIT, 1.0)


class TestOutput(unittest.TestCase):
    """Test output writing."""

    def test_write_json(self):
        records = [{"lat": 39.9, "lon": 116.4, "display_name": "Beijing"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            gc.write_output(records, path, as_json=True)
            with open(path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded[0]["lat"], 39.9)
        finally:
            os.unlink(path)


class TestQaSummary(unittest.TestCase):
    """Test the --qa sidecar summary (Phase 5 optimization)."""

    def _make_args(self, **kwargs):
        return argparse.Namespace(**kwargs)

    def test_write_qa_summary_batch(self):
        """write_qa_summary should record batch counts."""
        with tempfile.TemporaryDirectory() as tmp:
            qa_path = os.path.join(tmp, "run.qa.json")
            args = self._make_args(
                provider="nominatim",
                input="addresses.csv",
                address_col="address",
                output="out.json",
            )
            results = [
                {"geocode_status": "ok"},
                {"geocode_status": "ok"},
                {"geocode_status": "not_found"},
                {"geocode_status": "empty"},
            ]
            gc.write_qa_summary(qa_path, "batch", args, results)
            self.assertTrue(os.path.exists(qa_path))
            with open(qa_path) as f:
                data = json.load(f)
            self.assertEqual(data["skill"], "geocoding-skill")
            self.assertEqual(data["command"], "batch")
            self.assertEqual(data["provider"], "nominatim")
            self.assertEqual(data["input_csv"], "addresses.csv")
            self.assertEqual(data["total"], 4)
            self.assertEqual(data["ok"], 2)
            self.assertEqual(data["not_found"], 1)
            self.assertEqual(data["empty"], 1)
            self.assertEqual(data["output_path"], "out.json")
            self.assertIn("timestamp", data)

    def test_write_qa_summary_geocode(self):
        """write_qa_summary should record geocode inputs."""
        with tempfile.TemporaryDirectory() as tmp:
            qa_path = os.path.join(tmp, "subdir", "run.qa.json")
            args = self._make_args(
                provider="open-meteo",
                address="Tokyo",
                output="tokyo.json",
            )
            gc.write_qa_summary(qa_path, "geocode", args, [{"lat": 35.6, "lon": 139.6}])
            self.assertTrue(os.path.exists(qa_path))
            with open(qa_path) as f:
                data = json.load(f)
            self.assertEqual(data["command"], "geocode")
            self.assertEqual(data["provider"], "open-meteo")
            self.assertEqual(data["address"], "Tokyo")

    def test_parsers_accept_qa_flag(self):
        """All three high-use subcommands should accept --qa."""
        # Verify --qa is wired into the real main() parser by invoking
        # main() in-process via sys.argv and checking that it complains
        # about the *required* arg, not about --qa. The simplest way is to
        # check the help text.
        import subprocess
        for cmd in ("geocode", "reverse", "batch"):
            result = subprocess.run(
                [sys.executable,
                 os.path.join(os.path.dirname(__file__), "..", "scripts",
                              "geocoding-skill.py"),
                 cmd, "--help"],
                capture_output=True, text=True, timeout=15,
            )
            self.assertIn("--qa", result.stdout,
                          f"--qa not in help for subcommand {cmd}")


if __name__ == "__main__":
    unittest.main()
