"""Child-process entrypoint. No database imports, credentials or external tools executed from uploads."""

import resource
import sys
import json


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    kind, mime = sys.argv[1:3]
    raw = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Oversized task")
    from fastapi import HTTPException

    try:
        if kind in ("image", "qr"):
            from backend.app.services.images import analyze_image

            content, result = analyze_image(raw, mime, kind == "qr")
        elif kind == "code":
            from backend.app.services.code import scan_zip

            content, result = (
                "Uploaded source ZIP (original discarded)",
                scan_zip(raw, False),
            )
        elif kind == "voice":
            from backend.app.services.voice import analyze_voice

            content, result = analyze_voice(raw)
        else:
            raise HTTPException(422, "Unsupported scan type.")
        output = {"content": content, "result": result}
    except HTTPException as error:
        output = {"error": error.status_code}
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    main()
