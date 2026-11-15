"""Operator-only approved model download. Never called by scan handlers."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["tiny", "base", "small"], default="base")
    parser.add_argument("--directory", type=Path, default=Path("/models/whisper-base"))
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download

    repo = "Systran/faster-whisper-" + args.model
    info = HfApi().model_info(repo)
    snapshot_download(repo_id=repo, revision=info.sha, local_dir=args.directory)
    (args.directory / "scamshield-provenance.json").write_text(
        json.dumps(
            {
                "repository": repo,
                "revision": info.sha,
                "purpose": "local speech transcription; not deepfake detection",
            },
            indent=2,
        )
        + "\n"
    )
    print("Local model installed. Configure WHISPER_MODEL_PATH and restart the worker.")


if __name__ == "__main__":
    main()
