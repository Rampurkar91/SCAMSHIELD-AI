"""Fetch documented UCI mirrors through GitHub, record provenance, never commit raw data.
Run from repository root: python -m backend.scripts.download_datasets
"""

import base64, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1] / "datasets"
SOURCES = {
    "sms": {
        "repo": "justmarkham/pycon-2016-tutorial",
        "path": "data/sms.tsv",
        "file": "sms.tsv",
        "official": "https://archive.ics.uci.edu/dataset/228/sms+spam+collection",
        "license": "CC BY 4.0 (UCI dataset listing); cite original SMS Spam Collection creators",
        "description": "English ham/spam messages. Mirror counts may differ from the UCI catalog.",
    },
    "email": {
        "repo": "COM6012/ScalableML",
        "path": "Data/spambase.data",
        "file": "spambase.csv",
        "official": "https://archive.ics.uci.edu/dataset/94/spambase",
        "license": "CC BY 4.0 (UCI dataset listing); cite Hopkins, Reeber, Forman and Suermondt",
        "description": "57 numeric features and binary spam label; not raw email text or phishing labels.",
    },
}


def download(name):
    source = SOURCES[name]
    api = f"https://api.github.com/repos/{source['repo']}/contents/{source['path']}"
    with httpx.Client(timeout=30, follow_redirects=False) as c:
        r = c.get(
            api,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ScamShieldAI-dataset-fetcher",
            },
        )
        r.raise_for_status()
        payload = r.json()
        if not payload.get("content") or payload.get("encoding") != "base64":
            raise RuntimeError(
                "Expected a bounded GitHub contents response with base64 content."
            )
        raw = base64.b64decode(payload["content"], validate=False)
    if len(raw) > 5_000_000:
        raise ValueError("Unexpected dataset size")
    target = ROOT / name / source["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    meta = {
        **source,
        "name": name,
        "mirror_api": api,
        "github_blob_sha": payload["sha"],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "records_raw": len(raw.splitlines()),
        "redistributed": False,
    }
    (ROOT / "metadata" / f"{name}-source.json").write_text(
        json.dumps(meta, indent=2) + "\n"
    )
    print(f"{name}: downloaded {meta['records_raw']} lines, sha256={meta['sha256']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dataset", choices=["sms", "email", "all"], default="all", nargs="?"
    )
    args = parser.parse_args()
    for name in SOURCES if args.dataset == "all" else [args.dataset]:
        download(name)
