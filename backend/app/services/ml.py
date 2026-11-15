"""Only load operator-trained local artifacts. Joblib files are executable: never accept uploads."""

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=2)
def load_model(path, mtime):
    import joblib

    return joblib.load(path)


def predict_sms(content):
    path = Path(
        os.getenv("SMS_MODEL_PATH")
        or str(Path(__file__).resolve().parents[2] / "models" / "sms.joblib")
    )
    if not path.is_file():
        return {
            "status": "unavailable",
            "reason": "No trained SMS model installed; local rules remain active.",
        }
    try:
        model = load_model(str(path), path.stat().st_mtime_ns)
        return {
            "status": "ok",
            "label": str(model.predict([content])[0]),
            "source": "UCI English SMS spam baseline",
            "limitations": "Spam is not equivalent to fraud. This model is not validated for Hindi, Marathi, UPI or email phishing.",
        }
    except Exception:
        return {
            "status": "error",
            "reason": "Local model could not be loaded. Rule-based fallback remains active.",
        }
