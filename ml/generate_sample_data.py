"""Create a SYNTHETIC crime dataset so the whole app runs on day one.

!! This is fake data for development/demo only. Replace data/raw/crime.csv with a
real dataset (same columns) before your final evaluation. !!

Run from the project root:
    python -m ml.generate_sample_data
"""
import numpy as np
import pandas as pd

from ml.common import DATA_RAW

rng = np.random.default_rng(42)

CENTER = (16.1800, 75.6960)  # Bagalkote (approx.)
SPAN = 0.03                  # ~3 km around the centre

# (lat, lon, spread in degrees, share of incidents, night_bias)
HOTSPOTS = [
    (16.1850, 75.6900, 0.004, 0.28, 0.80),
    (16.1730, 75.7050, 0.005, 0.22, 0.70),
    (16.1900, 75.7100, 0.004, 0.18, 0.50),
    (16.1650, 75.6850, 0.006, 0.12, 0.60),
]
NOISE_SHARE = 1 - sum(h[3] for h in HOTSPOTS)

TYPES = {"Theft": 2, "Harassment": 3, "Assault": 5, "Snatching": 3, "Stalking": 4}
N = 4000


def random_hour(night_bias: float) -> int:
    if rng.random() < night_bias:
        return int(rng.choice([18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5]))
    return int(rng.integers(6, 18))


def main():
    rows = []
    shares = [h[3] for h in HOTSPOTS] + [NOISE_SHARE]
    for _ in range(N):
        k = rng.choice(len(shares), p=shares)
        if k < len(HOTSPOTS):
            lat0, lon0, spread, _, night = HOTSPOTS[k]
            lat = rng.normal(lat0, spread)
            lon = rng.normal(lon0, spread)
            hour = random_hour(night)
        else:  # background noise anywhere in the area
            lat = rng.uniform(CENTER[0] - SPAN, CENTER[0] + SPAN)
            lon = rng.uniform(CENTER[1] - SPAN, CENTER[1] + SPAN)
            hour = int(rng.integers(0, 24))
        crime = rng.choice(list(TYPES))
        date = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 730)))
        rows.append({
            "incident_type": crime,
            "date": date.date().isoformat(),
            "hour": hour,
            "day_of_week": date.dayofweek,
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
            "severity": TYPES[crime],
        })

    DATA_RAW.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(DATA_RAW, index=False)
    print(f"Saved {len(rows)} synthetic incidents to {DATA_RAW}")


if __name__ == "__main__":
    main()
