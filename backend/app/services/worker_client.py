"""Production file scans fail closed unless a separate worker is configured."""

import os
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    score: int = Field(ge=0, le=100)
    level: Literal["low", "moderate", "high", "critical"]
    status: str
    summary: str = Field(max_length=4000)
    indicators: list = Field(max_length=200)
    details: dict
    actions: list[str] = Field(max_length=20)
    urls: list[str] = Field(max_length=100)
    provider: dict
    limitations: list[str] = Field(max_length=30)


class WorkerResponse(BaseModel):
    content: str = Field(max_length=12000)
    result: WorkerResult


def worker_base_url():
    direct = os.getenv("SCANNER_WORKER_URL", "").rstrip("/")
    return direct or (
        "http://" + os.environ["SCANNER_WORKER_HOST"] + ":8090"
        if os.getenv("SCANNER_WORKER_HOST")
        else ""
    )


def scan_in_worker(kind: str, raw: bytes, mime: str, dependencies=False):
    url = worker_base_url()
    key = os.getenv("SCANNER_WORKER_KEY", "")
    if not url:
        if os.getenv("APP_ENV") == "production":
            raise HTTPException(
                503,
                "Isolated scanner worker is not configured. File analysis is disabled.",
            )
        # Explicit development-only path. Never fall back locally in production.
        from .images import analyze_image
        from .code import scan_zip
        from .voice import analyze_voice

        if kind in ("image", "qr"):
            return analyze_image(raw, mime, kind == "qr")
        if kind == "voice":
            return analyze_voice(raw)
        if kind == "code":
            return "Uploaded source ZIP (original discarded)", scan_zip(
                raw, dependencies
            )
        raise HTTPException(422, "Unsupported isolated scan type.")
    parsed = urlsplit(url)
    if (
        not key
        or len(key) < 32
        or parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(503, "Scanner worker configuration is invalid.")
    try:
        with httpx.Client(timeout=100, follow_redirects=False) as client:
            response = client.post(
                url + "/scan/" + kind,
                content=raw,
                headers={"X-Worker-Key": key, "Content-Type": mime},
            )
            if response.status_code in (413, 415, 422, 429, 503):
                reasons = {
                    413: "Upload exceeds scanner limits.",
                    415: "Unsupported upload format.",
                    422: "The scanner could not read valid content from this file.",
                    429: "Scanner worker is busy. Try again shortly.",
                    503: "Scanner software or model is unavailable. Contact the administrator.",
                }
                raise HTTPException(response.status_code, reasons[response.status_code])
            response.raise_for_status()
            if len(response.content) > 2 * 1024 * 1024:
                raise ValueError()
            parsed = WorkerResponse.model_validate(response.json())
            result = parsed.result.model_dump()
            if dependencies:
                from ..integrations.providers import osv_query
                import re

                osv = []
                for item in result["details"].get("dependencies", [])[:10]:
                    if not isinstance(item, dict) or item.get("ecosystem") not in (
                        "PyPI",
                        "npm",
                    ):
                        continue
                    name, version = item.get("name", ""), item.get("version", "")
                    if (
                        not isinstance(name, str)
                        or not isinstance(version, str)
                        or not re.fullmatch(r"[\w@./-]{1,150}", name)
                        or not re.fullmatch(r"[\w.+-]{1,100}", version)
                    ):
                        continue
                    osv.append(
                        {
                            "package": name,
                            "version": version,
                            **osv_query(item["ecosystem"], name, version),
                        }
                    )
                result["details"]["osv"] = osv
                if any(item["ids"] for item in osv):
                    result["score"] = max(result["score"], 70)
                    result["level"] = "critical" if result["score"] >= 80 else "high"
                    result["status"] = "dangerous"
            return parsed.content, result
    except (httpx.HTTPError, ValueError):
        raise HTTPException(
            503,
            "Isolated scanner failed or timed out. No scan was saved; no local fallback was attempted.",
        )
