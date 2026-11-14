import os
import httpx


def runtime_status():
    from .worker_client import worker_base_url

    url = worker_base_url()
    mode = (
        "isolated_worker"
        if url
        else "disabled"
        if os.getenv("APP_ENV") == "production"
        else "development_local"
    )
    result = {
        "processing_mode": mode,
        "worker": "not_configured",
        "ocr": False,
        "voice": False,
        "smtp_configured": bool(
            os.getenv("SMTP_HOST")
            and (os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM"))
        ),
        "provider_configuration_note": "Credentials must be supplied by the deployment owner; configured does not mean verified.",
    }
    if url:
        try:
            with httpx.Client(timeout=3, follow_redirects=False) as client:
                response = client.get(
                    url + "/health",
                    headers={"X-Worker-Key": os.getenv("SCANNER_WORKER_KEY", "")},
                )
                response.raise_for_status()
                data = response.json()
                result.update(
                    worker="reachable",
                    ocr=data.get("ocr_installed") is True,
                    voice=data.get("voice_model_installed") is True,
                )
        except (httpx.HTTPError, ValueError):
            result["worker"] = "unavailable"
    elif mode == "development_local":
        from .tool_status import tool_status

        status = tool_status()
        result.update(
            ocr=status["ocr_installed"], voice=status["voice_model_installed"]
        )
    return result
