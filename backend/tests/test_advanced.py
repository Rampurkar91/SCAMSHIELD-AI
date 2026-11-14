import io, zipfile, wave
from types import SimpleNamespace
import pytest
from PIL import Image
from backend.tests.test_core import client, account, clear_limit
from backend.app.integrations import providers
from backend.app.services.images import decode_image
from backend.app.services.analysis import enrich
from backend.app.services.code import scan_zip
from backend.app.services.ml import predict_sms


def png():
    out = io.BytesIO()
    Image.new("RGB", (300, 180), "white").save(out, format="PNG")
    return out.getvalue()


def zipped(name="app.py", text='print("hello")'):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(name, text)
    return out.getvalue()


def qr_png(payload):
    import cv2
    import numpy as np

    data = cv2.QRCodeEncoder_create().encode(payload)
    data = np.pad(data, 12, constant_values=255)
    data = cv2.resize(data, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
    return cv2.imencode(".png", data)[1].tobytes()


def test_image_mime_and_limits():
    from fastapi import HTTPException

    assert decode_image(png(), "image/png").size == (300, 180)
    for raw, mime, code in [
        (png(), "image/jpeg", 415),
        (b"bad", "image/png", 422),
        (png(), "text/plain", 415),
        (b"x" * (5 * 1024 * 1024 + 1), "image/png", 413),
    ]:
        with pytest.raises(HTTPException) as e:
            decode_image(raw, mime)
        assert e.value.status_code == code


def test_qr_decode_and_private_persistence():
    h, _ = account()
    other, _ = account()
    response = client.post(
        "/api/scans/qr",
        headers=h,
        files={
            "file": ("qr.png", qr_png("upi://pay?pa=shop%40upi&am=200"), "image/png")
        },
    )
    assert response.status_code == 201, response.text
    r = response.json()
    assert r["kind"] == "qr"
    assert r["result"]["details"]["payment_intent"]["amount"] == "200"
    assert "Authorizing" in r["result"]["details"]["payment_intent"]["action"]
    assert client.get("/api/history/" + str(r["id"]), headers=other).status_code == 404


def test_ocr_mock_and_unavailable(monkeypatch):
    import pytesseract

    h, _ = account()
    monkeypatch.setattr(
        pytesseract,
        "image_to_string",
        lambda *a, **k: "Send your OTP immediately. Your account is blocked.",
    )
    r = client.post(
        "/api/scans/image", headers=h, files={"file": ("test.png", png(), "image/png")}
    )
    assert r.status_code == 201 and r.json()["score"] >= 80

    def absent(*a, **k):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_string", absent)
    assert (
        client.post(
            "/api/scans/image",
            headers=h,
            files={"file": ("test.png", png(), "image/png")},
        ).status_code
        == 503
    )


def test_code_never_returns_secret_value():
    r = scan_zip(zipped(text='api_key="EXAMPLE-NOT-A-REAL-SECRET"\neval(user_input)'))
    assert r["score"] >= 60
    assert "EXAMPLE-NOT-A-REAL-SECRET" not in str(r)
    assert r["details"]["findings"][0]["line"] == 1
    assert scan_zip(zipped())["score"] == 0


def test_zip_path_traversal_and_limits():
    from fastapi import HTTPException

    for raw in [
        zipped("../outside.py"),
        zipped("/absolute.py"),
        b"not-a-zip",
        zipped(text="x" * 600000),
    ]:
        with pytest.raises(HTTPException):
            scan_zip(raw)


def test_code_api_and_eml():
    h, _ = account()
    r = client.post(
        "/api/scans/code",
        headers=h,
        files={
            "file": ("src.zip", zipped(text="eval(request.data)"), "application/zip")
        },
    )
    assert r.status_code == 201, r.text
    eml = b"From: Stranger <s@example.com>\nSubject: Urgent KYC\nContent-Type: text/plain; charset=utf-8\n\nAccount blocked immediately. Send your OTP."
    r = client.post(
        "/api/scans/email-file",
        headers=h,
        files={"file": ("email.eml", eml, "message/rfc822")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["result"]["details"]["subject"] == "Urgent KYC"


def test_voice_consent_and_missing_model(monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL_PATH", raising=False)
    h, _ = account()
    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 32000)
    files = {"file": ("voice.wav", out.getvalue(), "audio/wav")}
    assert client.post("/api/scans/voice", headers=h, files=files).status_code == 422
    assert (
        client.post(
            "/api/scans/voice", headers=h, files=files, data={"consent": "true"}
        ).status_code
        == 503
    )


def test_ai_fallback_and_no_pretend_answer(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    h, _ = account()
    r = client.post(
        "/api/assistant/chat",
        headers=h,
        json={
            "message": "How do I stop a UPI scam?",
            "language": "Marathi",
            "use_ai": True,
        },
    )
    assert r.status_code == 200 and r.json()["status"] == "not_configured"
    assert r.json()["source"].startswith("Static safety fallback")
    assert "1930" in r.json()["explanation"]
    assert client.get("/api/admin/integrations/status", headers=h).status_code == 403


def test_quiz_saved_and_notifications_isolated():
    h, _ = account()
    other, _ = account()
    quiz = client.get("/api/awareness/quizzes", headers=h).json()["quizzes"][0]
    assert "correct" not in quiz
    assert (
        client.post(
            "/api/awareness/quizzes/upi-pin/submit", headers=h, json={"answer": 1}
        ).json()["score"]
        == 100
    )
    assert len(client.get("/api/awareness/quizzes", headers=h).json()["attempts"]) == 1
    assert client.get("/api/awareness/quizzes", headers=other).json()["attempts"] == []
    client.post(
        "/api/scans/message",
        headers=h,
        json={"content": "Urgent account blocked immediately. Send your OTP now."},
    )
    items = client.get("/api/notifications", headers=h).json()
    assert len(items) == 1
    assert (
        client.put(
            f"/api/notifications/{items[0]['id']}/read", headers=other
        ).status_code
        == 404
    )
    assert (
        client.put(f"/api/notifications/{items[0]['id']}/read", headers=h).status_code
        == 200
    )


def test_provider_missing_keys(monkeypatch):
    for name, key in providers.PROVIDERS.items():
        monkeypatch.delenv(key, raising=False)
        if name != "gemini":
            assert (
                providers.check_url(name, "https://example.com")["status"]
                == "not_configured"
            )


def fake_http(monkeypatch, data, status=200, throws=False):
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *a, **k):
            if throws:
                raise providers.httpx.ConnectError("do not echo private errors")
            return providers.httpx.Response(
                status,
                json=data,
                request=providers.httpx.Request("POST", "https://provider.invalid"),
            )

        get = post

    monkeypatch.setattr(providers.httpx, "Client", FakeClient)


def test_safe_browsing_match_and_rate_limit(monkeypatch):
    monkeypatch.setenv("GOOGLE_SAFE_BROWSING_API_KEY", "test-only-not-real")
    fake_http(monkeypatch, {"matches": [{"threatType": "SOCIAL_ENGINEERING"}]})
    assert (
        providers.check_url("safe_browsing", "https://example.com")["status"]
        == "matched"
    )
    fake_http(monkeypatch, {}, 429)
    assert (
        providers.check_url("safe_browsing", "https://example.com")["status"]
        == "rate_limited"
    )


def test_provider_failures_and_validation(monkeypatch):
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-only-not-real")
    fake_http(monkeypatch, {"query_status": "invalid_key"})
    assert providers.check_url("urlhaus", "https://example.com")["status"] == "error"
    fake_http(monkeypatch, {}, throws=True)
    r = providers.check_url("urlhaus", "https://example.com")
    assert r["status"] == "error" and "private errors" not in str(r)


def test_reputation_separate_from_ai_and_score_floor(monkeypatch):
    from backend.app.services import analysis

    monkeypatch.setattr(
        analysis,
        "check_url",
        lambda name, url: {
            "provider": name,
            "status": "matched",
            "category": "malware_distribution",
            "reason": "Mocked test fixture",
        },
    )
    r = enrich("url", "https://example.com", external=True)
    assert r["score"] == 90 and r["ai"]["status"] == "not_requested"
    assert len([e for e in r["indicators"] if e["code"] == "known_threat_match"]) == 1


def test_model_missing_fallback(monkeypatch):
    monkeypatch.setenv("SMS_MODEL_PATH", "/path/does/not/exist.joblib")
    assert predict_sms("hello")["status"] == "unavailable"


def test_health_database():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["database"] == "connected"


def test_github_requires_explicit_authorization_and_fixed_host():
    from fastapi import HTTPException
    from backend.app.services.github import scan_github

    h, _ = account()
    assert (
        client.post(
            "/api/scans/github",
            headers=h,
            json={"url": "https://github.com/example/repo"},
        ).status_code
        == 422
    )
    for url in [
        "http://github.com/example/repo",
        "https://evil.example/repo",
        "https://github.com/a/b?x=y",
        "https://github.com/a/../",
    ]:
        with pytest.raises(HTTPException) as e:
            scan_github(url)
        assert e.value.status_code == 422


def test_admin_review_and_integration_status():
    from backend.app.database import SessionLocal, User
    from sqlalchemy import select

    h, email = account()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        user.role = "admin"
        db.commit()
    status = client.get("/api/admin/integrations/status", headers=h)
    assert status.status_code == 200
    assert {p["name"] for p in status.json()} == set(providers.PROVIDERS)
    assert "GEMINI_API_KEY" not in status.text
    assert client.get("/api/admin/dashboard", headers=h).json()["users"] >= 1


def test_trained_sms_model_if_available():
    from pathlib import Path

    if not Path("backend/models/sms.joblib").exists():
        pytest.skip("Run the documented training command to produce a trusted model.")
    result = predict_sms("Hello, are we still meeting for lunch tomorrow?")
    assert result["status"] == "ok" and result["label"] in ("ham", "spam")


def test_gemini_structured_response_and_bad_output(monkeypatch):
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")

    class Fake:
        text = '{"explanation":"Verify independently.","actions":["Do not share secrets."],"uncertainty":"This is not independent verification."}'

        def __init__(self, **kw):
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def generate_content(self, **kw):
            return SimpleNamespace(text=self.text)

    monkeypatch.setattr(genai, "Client", Fake)
    assert providers.gemini_answer("Question about UPI")["status"] == "ok"
    Fake.text = "not valid JSON"
    assert providers.gemini_answer("Question about UPI")["status"] == "error"


def test_voice_transcript_pipeline_with_mock_local_model(monkeypatch, tmp_path):
    from backend.app.services import voice

    monkeypatch.setenv("WHISPER_MODEL_PATH", str(tmp_path))

    class Model:
        def transcribe(self, path, **kwargs):
            return iter(
                [
                    SimpleNamespace(
                        text="Urgent account blocked immediately. Send your OTP."
                    )
                ]
            ), None

    monkeypatch.setattr(voice, "whisper_model", lambda path: Model())
    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 32000)
    text, result = voice.analyze_voice(out.getvalue())
    assert result["score"] >= 80 and result["details"]["duration_seconds"] == 2
    assert "cannot establish" in result["details"]["deepfake_detection"]
