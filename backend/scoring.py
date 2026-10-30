"""Turn routes into safety scores and pick the best one.

Idea (explain this in your viva):
  1. Walk along each route and take a sample point every 50 m.
  2. Ask the ML model for the risk (0-1) at each sample point.
  3. Route risk = average of those risks.
  4. cost = w_safety * risk + w_time * extra_time + w_dist * extra_distance
     (extra_* = how much slower/longer than the best option, capped at 1)
  5. Lowest cost = recommended route.
"""
import math

import numpy as np

from ml.common import time_bucket
from ml.risk_model import predict_risk

EARTH_RADIUS_M = 6_371_000
LOW_RISK_BELOW = 0.25     # tune these two after training on your real data
HIGH_RISK_FROM = 0.44


def haversine(lat1, lon1, lat2, lon2):
    """Distance in metres between two lat/lon points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def sample_route(coords, step_m=50):
    """coords = [[lon, lat], ...]. Returns [(lat, lon), ...] roughly every step_m metres."""
    if not coords:
        return []
    points = [(coords[0][1], coords[0][0])]
    since_last = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        seg = haversine(lat1, lon1, lat2, lon2)
        if seg == 0:
            continue
        travelled = 0.0
        while since_last + (seg - travelled) >= step_m:
            travelled += step_m - since_last
            since_last = 0.0
            f = travelled / seg
            points.append((lat1 + (lat2 - lat1) * f, lon1 + (lon2 - lon1) * f))
        since_last += seg - travelled
    points.append((coords[-1][1], coords[-1][0]))
    return points


def risk_level(risk):
    if risk < LOW_RISK_BELOW:
        return "Low"
    if risk < HIGH_RISK_FROM:
        return "Medium"
    return "High"


def _extra(value, best):
    return min((value - best) / best, 1.0) if best > 0 else 0.0


def score_routes(routes, hour, w_safety=0.5):
    """routes: output of routing.get_routes(). Returns scored routes for the frontend."""
    w_safety = min(max(float(w_safety), 0.0), 1.0)
    rest = 1.0 - w_safety
    w_time, w_dist = 0.6 * rest, 0.4 * rest
    bucket = time_bucket(hour)

    scored = []
    for i, r in enumerate(routes):
        pts = sample_route(r["coords"])
        risks = np.asarray(predict_risk([p[0] for p in pts], [p[1] for p in pts], bucket),
                           dtype=float)
        risk = float(risks.mean()) if len(risks) else 0.0
        scored.append({
            "id": i,
            "path": [[lat, lon] for lon, lat in r["coords"]],
            "distance_km": round(r["distance_m"] / 1000, 2),
            "duration_min": round(r["duration_s"] / 60, 1),
            "risk": round(risk, 3),
            "safety_score": int(round(100 * (1 - risk))),
            "risk_level": risk_level(risk),
            "high_risk_share": round(float((risks > 0.6).mean()) if len(risks) else 0.0, 3),
            "_dur": r["duration_s"],
            "_dist": r["distance_m"],
        })

    best_t = min(s["_dur"] for s in scored)
    best_d = min(s["_dist"] for s in scored)
    for s in scored:
        s["cost"] = round(w_safety * s["risk"]
                          + w_time * _extra(s.pop("_dur"), best_t)
                          + w_dist * _extra(s.pop("_dist"), best_d), 4)
        s["tags"] = []

    min(scored, key=lambda s: s["cost"])["tags"].append("Recommended")
    min(scored, key=lambda s: s["risk"])["tags"].append("Safest")
    min(scored, key=lambda s: s["duration_min"])["tags"].append("Fastest")
    return scored
