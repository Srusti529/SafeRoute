"""Shared paths and helpers used by the ML scripts AND the Flask backend."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw" / "crime.csv"
MODEL_DIR = ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"
HOTSPOT_PATH = MODEL_DIR / "hotspots.json"

TIME_BUCKETS = {
    0: "Night (00:00-05:59)",
    1: "Morning (06:00-11:59)",
    2: "Afternoon (12:00-17:59)",
    3: "Evening (18:00-23:59)",
}


def time_bucket(hour) -> int:
    """Convert an hour (0-23) into one of 4 time-of-day buckets."""
    hour = int(hour) % 24
    if hour < 6:
        return 0
    if hour < 12:
        return 1
    if hour < 18:
        return 2
    return 3
