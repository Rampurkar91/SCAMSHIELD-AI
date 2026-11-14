"""Reproducible baselines. Held-out metrics are not deployment guarantees."""

import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


def train(task, input_path=None):
    if task == "sms":
        source = Path(input_path) if input_path else ROOT / "datasets/sms/sms.tsv"
        df = (
            pd.read_csv(source, sep="\t", header=None, names=["label", "text"])
            .dropna()
            .drop_duplicates("text")
        )
        if not set(df.label) <= {"ham", "spam"}:
            raise ValueError("Expected ham/spam labels.")
        X = df.text.str.strip()
        y = df.label
        pipeline = make_pipeline(
            TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=2,
                max_features=30000,
            ),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        )
    elif task == "email":
        source = (
            Path(input_path) if input_path else ROOT / "datasets/email/spambase.csv"
        )
        df = pd.read_csv(source, header=None).dropna().drop_duplicates()
        if df.shape[1] != 58:
            raise ValueError("Spambase requires 57 numeric features plus label.")
        X = df.iloc[:, :57].astype(float)
        y = df.iloc[:, 57].map({0: "ham", 1: "spam"})
        pipeline = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
        )
    else:
        if not input_path:
            raise ValueError(
                "URL training requires your licensed CSV with url,label columns; no unlicensed feed is assumed."
            )
        source = Path(input_path)
        df = pd.read_csv(source).dropna(subset=["url", "label"]).drop_duplicates("url")
        if not set(df.label) <= {"benign", "phishing", "malware"}:
            raise ValueError(
                "URL labels must distinguish benign, phishing and malware."
            )
        if df.label.nunique() < 2:
            raise ValueError(
                "Training requires at least two independently labeled classes, not a threat-only feed."
            )
        X = df.url
        y = df.label
        pipeline = make_pipeline(
            TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=40000),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        )
    if y.isna().any():
        raise ValueError("Unexpected labels.")
    xtrain, xtest, ytrain, ytest = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    pipeline.fit(xtrain, ytrain)
    pred = pipeline.predict(xtest)
    labels = list(pipeline.classes_)
    precision, recall, f1, _ = precision_recall_fscore_support(
        ytest, pred, average="weighted", zero_division=0
    )
    cm = confusion_matrix(ytest, pred, labels=labels)
    false_positive = None
    if set(labels) == {"ham", "spam"}:
        i = labels.index("ham")
        j = labels.index("spam")
        false_positive = float(cm[i, j] / cm[i].sum())
    per_class = precision_recall_fscore_support(
        ytest, pred, labels=labels, zero_division=0
    )
    metrics = {
        "task": task,
        "seed": 42,
        "raw_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "records_after_deduplication": len(df),
        "train_records": len(xtrain),
        "test_records": len(xtest),
        "accuracy": accuracy_score(ytest, pred),
        "weighted_precision": precision,
        "weighted_recall": recall,
        "weighted_f1": f1,
        "labels": labels,
        "per_class": {
            label: {
                "precision": float(per_class[0][i]),
                "recall": float(per_class[1][i]),
                "f1": float(per_class[2][i]),
            }
            for i, label in enumerate(labels)
        },
        "confusion_matrix": cm.tolist(),
        "false_positive_rate_ham_as_spam": false_positive,
        "limitations": "Random split may overestimate generalization. Not a calibrated fraud detector. Email model requires numeric Spambase features, not raw email text. URL models require domain/time-separated evaluation before deployment.",
    }
    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump(pipeline, ROOT / "models" / f"{task}.joblib")
    (ROOT / "datasets/metadata" / f"{task}-metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("task", choices=["sms", "email", "url"])
    p.add_argument("--input")
    a = p.parse_args()
    train(a.task, a.input)
