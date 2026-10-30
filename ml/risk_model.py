"""Load the trained model and predict a 0-1 risk value for map points."""
import joblib
import numpy as np
import pandas as pd

from ml.common import MODEL_PATH

# Meaning of the classes the model learns: 0 = Low, 1 = Medium, 2 = High.
# Expected risk = sum(probability of class * weight of class)
CLASS_WEIGHT = {0: 0.0, 1: 0.5, 2: 1.0}

_model = None


def load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError("Model not found. Run:  python -m ml.train")
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_risk(lats, lons, bucket: int):
    """Return a numpy array of risk values (0 = safest, 1 = riskiest)."""
    model = load_model()
    X = pd.DataFrame({"lat": list(lats), "lon": list(lons), "bucket": int(bucket)})
    proba = model.predict_proba(X[["lat", "lon", "bucket"]])
    weights = np.array([CLASS_WEIGHT[int(c)] for c in model.classes_])
    return proba @ weights
