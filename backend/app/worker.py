"""Internal-only bounded scanner gateway. Run in the hardened worker container, not the API.
Each scan uses a disposable subprocess; wall timeout kills its entire process group.
"""

import asyncio
import hmac
import json
import os
import signal
import sys
from typing import Literal
from fastapi import FastAPI, Request, HTTPException
from .services.worker_client import WorkerResponse

app = FastAPI(
    title="ScamShield isolated scanner", docs_url=None, redoc_url=None, openapi_url=None
)
semaphore = asyncio.Semaphore(1)


@app.get("/health")
def health(request: Request):
    expected = os.getenv("SCANNER_WORKER_KEY", "")
    if len(expected) < 32 or not hmac.compare_digest(
        request.headers.get("x-worker-key", ""), expected
    ):
        raise HTTPException(401, "Worker authentication required.")
    from .services.tool_status import tool_status

    return {
        "status": "ok",
        "isolation": "separate-service-disposable-process",
        **tool_status(),
    }


@app.post("/scan/{kind}")
async def scan(kind: Literal["image", "qr", "voice", "code"], request: Request):
    expected = os.getenv("SCANNER_WORKER_KEY", "")
    if len(expected) < 32 or not hmac.compare_digest(
        request.headers.get("x-worker-key", ""), expected
    ):
        raise HTTPException(401, "Worker authentication required.")
    if semaphore.locked():
        raise HTTPException(429, "Worker busy.")
    async with semaphore:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8 * 1024 * 1024:
                raise HTTPException(413, "Oversized file.")
        # Allowlist environment: the child has no database URL, JWT/SMTP/provider/worker secrets.
        child_env = {
            k: v
            for k, v in os.environ.items()
            if k
            in {
                "PATH",
                "LANG",
                "LC_ALL",
                "TESSERACT_CMD",
                "OCR_LANG",
                "WHISPER_MODEL_PATH",
                "LD_LIBRARY_PATH",
            }
        }
        child_env.update(
            HOME="/tmp",
            TMPDIR="/tmp",
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
            PYTHONUNBUFFERED="1",
            SMS_MODEL_PATH="/nonexistent-model",
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "backend.app.worker_task",
            kind,
            request.headers.get("content-type", "application/octet-stream"),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=child_env,
            start_new_session=True,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(bytes(body)), timeout=95
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
            raise HTTPException(503, "Scanner timed out.")
        if process.returncode or len(stdout) > 2 * 1024 * 1024:
            raise HTTPException(503, "Scanner failed.")
        try:
            output = json.loads(stdout)
            if "error" in output:
                code = (
                    output["error"] if output["error"] in (413, 415, 422, 503) else 503
                )
                raise HTTPException(code, "Scanner could not complete analysis.")
            return WorkerResponse.model_validate(output).model_dump()
        except (ValueError, TypeError):
            raise HTTPException(503, "Invalid scanner output.")
