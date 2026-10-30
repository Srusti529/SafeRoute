"""Run from the project root:  python -m unittest discover -s tests -v"""
import unittest
from unittest.mock import patch

import numpy as np

from backend import scoring
from ml.common import time_bucket


class HelperTests(unittest.TestCase):
    def test_haversine_one_degree_latitude(self):
        self.assertAlmostEqual(scoring.haversine(0, 0, 1, 0) / 1000, 111.19, places=1)

    def test_sample_route_spacing(self):
        # ~1.11 km straight line north -> about one point every 50 m
        pts = scoring.sample_route([[75.0, 16.0], [75.0, 16.01]], step_m=50)
        self.assertTrue(20 <= len(pts) <= 25)

    def test_time_bucket(self):
        self.assertEqual([time_bucket(h) for h in (0, 6, 12, 18, 23)], [0, 1, 2, 3, 3])


class ScoringTests(unittest.TestCase):
    def setUp(self):
        # Route 0: short but risky.  Route 1: a bit longer but safe.
        self.routes = [
            {"coords": [[75.00, 16.0], [75.00, 16.02]], "distance_m": 2200, "duration_s": 300},
            {"coords": [[75.10, 16.0], [75.10, 16.02]], "distance_m": 2600, "duration_s": 360},
        ]

    def _fake_risk(self, lats, lons, bucket):
        return np.where(np.array(lons) < 75.05, 0.8, 0.05)

    def test_safety_priority_prefers_safe_route(self):
        with patch.object(scoring, "predict_risk", self._fake_risk):
            out = scoring.score_routes(self.routes, hour=22, w_safety=0.9)
        recommended = next(r for r in out if "Recommended" in r["tags"])
        self.assertEqual(recommended["id"], 1)
        self.assertEqual(out[0]["risk_level"], "High")

    def test_speed_priority_prefers_fast_route_when_risk_equal(self):
        with patch.object(scoring, "predict_risk", lambda la, lo, b: np.full(len(la), 0.1)):
            out = scoring.score_routes(self.routes, hour=10, w_safety=0.1)
        recommended = next(r for r in out if "Recommended" in r["tags"])
        self.assertEqual(recommended["id"], 0)


if __name__ == "__main__":
    unittest.main()
