"""Create missing root deployment secrets without printing them or overwriting existing settings."""

import secrets
from pathlib import Path


def main():
    path = Path(__file__).resolve().parents[2] / ".env"
    current = path.read_text() if path.exists() else ""
    keys = {
        line.split("=", 1)[0].strip()
        for line in current.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    additions = [
        name + "=" + secrets.token_hex(32)
        for name in ("POSTGRES_PASSWORD", "JWT_SECRET_KEY", "SCANNER_WORKER_KEY")
        if name not in keys
    ]
    if additions:
        path.write_text(current.rstrip() + "\n" + "\n".join(additions) + "\n")
        path.chmod(0o600)
    print(
        "Local deployment secrets are present in the ignored root .env. Values were not printed."
    )


if __name__ == "__main__":
    main()
