"""Train the hotspot (K-Means) and risk (Random Forest) models.

Run from the project root:
    python -m ml.train

Input : data/raw/crime.csv  with columns  lat, lon, hour, severity
Output: ml/models/risk_model.joblib  and  ml/models/hotspots.json
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.common import DATA_RAW, HOTSPOT_PATH, MODEL_DIR, MODEL_PATH, time_bucket

REQUIRED = ["lat", "lon", "hour", "severity"]
CELL = 0.002  # grid cell size in degrees (about 200 m)


def load_data() -> pd.DataFrame:
    if not DATA_RAW.exists():
        raise SystemExit(
            f"{DATA_RAW} not found.\n"
            "Run `python -m ml.generate_sample_data` or put your own CSV there."
        )
    df = pd.read_csv(DATA_RAW)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV is missing required columns: {missing}")
    df = df.dropna(subset=REQUIRED)
    df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]
    df["bucket"] = df["hour"].astype(int).map(time_bucket)
    print(f"Loaded {len(df)} clean incidents")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- hotspots
def build_hotspots(df: pd.DataFrame, k: int = 6) -> list:
    """K-Means on coordinates; label each cluster Low / Medium / High."""
    k = max(1, min(k, len(df)))
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(df[["lat", "lon"]])
    df = df.assign(cluster=km.labels_)

    severity_sum = df.groupby("cluster")["severity"].sum()
    pct = severity_sum.rank(pct=True)

    hotspots = []
    for c, (lat, lon) in enumerate(km.cluster_centers_):
        pts = df[df["cluster"] == c]
        dlat = (pts["lat"] - lat) * 111_000
        dlon = (pts["lon"] - lon) * 111_000 * np.cos(np.radians(lat))
        radius = float(np.percentile(np.hypot(dlat, dlon), 90))
        level = "High" if pct[c] > 0.7 else "Medium" if pct[c] > 0.4 else "Low"
        hotspots.append({
            "lat": float(lat), "lon": float(lon), "level": level,
            "incidents": int(len(pts)), "radius_m": round(radius, 1),
        })
    return hotspots


# -------------------------------------------------------------- risk model
def build_training_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate incidents into (grid cell x time bucket) rows with a risk class."""
    df = df.assign(ix=np.floor(df["lat"] / CELL).astype(int),
                   iy=np.floor(df["lon"] / CELL).astype(int))
    agg = df.groupby(["ix", "iy", "bucket"])["severity"].sum().rename("score")

    ix_range = range(df["ix"].min(), df["ix"].max() + 1)
    iy_range = range(df["iy"].min(), df["iy"].max() + 1)
    full = pd.MultiIndex.from_product([ix_range, iy_range, range(4)],
                                      names=["ix", "iy", "bucket"])
    table = agg.reindex(full, fill_value=0).reset_index()

    nonzero = table.loc[table["score"] > 0, "score"]
    t1, t2 = np.percentile(nonzero, [50, 85]) if len(nonzero) else (1, 2)
    table["risk_class"] = np.where(table["score"] >= t2, 2,
                                   np.where(table["score"] >= t1, 1, 0))
    table["lat"] = (table["ix"] + 0.5) * CELL
    table["lon"] = (table["iy"] + 0.5) * CELL
    return table


def train_models(table: pd.DataFrame):
    X = table[["lat", "lon", "bucket"]]
    y = table["risk_class"]
    stratify = y if y.value_counts().min() >= 2 else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify)

    rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                random_state=42, n_jobs=-1).fit(X_tr, y_tr)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_tr, y_tr)

    print("\n=== Model comparison (put this table in your report) ===")
    print(f"Logistic Regression accuracy: {accuracy_score(y_te, lr.predict(X_te)):.3f}")
    print(f"Random Forest accuracy      : {accuracy_score(y_te, rf.predict(X_te)):.3f}")
    print("\nRandom Forest detail (0=Low, 1=Medium, 2=High):")
    print(classification_report(y_te, rf.predict(X_te), zero_division=0))
    return rf


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()

    hotspots = build_hotspots(df)
    HOTSPOT_PATH.write_text(json.dumps(hotspots, indent=2))
    print(f"Saved {len(hotspots)} hotspots -> {HOTSPOT_PATH}")

    model = train_models(build_training_table(df))
    joblib.dump(model, MODEL_PATH)
    print(f"Saved risk model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
