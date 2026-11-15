import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, parse_qs
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.tests.test_core import client, account, clear_limit  # noqa: F401 - autouse fixture
from backend.tests.test_advanced import qr_png, zipped
from backend.app.database import SessionLocal, EmailVerification, User
from backend.app.services import family, worker_client
from sqlalchemy import select


def verified_account():
    headers, email = account()
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    with SessionLocal() as db:
        db.add(
            EmailVerification(user_id=user_id, verified_at=datetime.now(timezone.utc))
        )
        db.commit()
    return headers, email, user_id


def capture_mail(monkeypatch):
    messages = []
    monkeypatch.setattr(
        family,
        "send_email",
        lambda to, subject, body: messages.append(
            {"to": to, "subject": subject, "body": body}
        ),
    )
    return messages


def token_from(message, key="token"):
    url = re.search(r"https?://\S+", message["body"]).group(0)
    return parse_qs(urlsplit(url).query)[key][0]


def test_verification_single_use_cooldown_and_identity(monkeypatch):
    messages = capture_mail(monkeypatch)
    h, email = account()
    assert client.get("/api/auth/me", headers=h).json()["email_verified"] is False
    assert client.post("/api/auth/send-verification", headers=h).status_code == 200
    assert messages[0]["to"] == email
    token = token_from(messages[0])
    assert token not in client.get("/api/auth/me", headers=h).text
    assert client.post("/api/auth/send-verification", headers=h).status_code == 429
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    )
    assert (
        client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    )
    assert client.get("/api/auth/me", headers=h).json()["email_verified"] is True


def test_expired_verification_and_no_unverified_family(monkeypatch):
    messages = capture_mail(monkeypatch)
    h, email = account()
    assert (
        client.post("/api/families", headers=h, json={"name": "Our family"}).status_code
        == 403
    )
    client.post("/api/auth/send-verification", headers=h)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        row = db.get(EmailVerification, user.id)
        row.expires = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert (
        client.post(
            "/api/auth/verify-email", json={"token": token_from(messages[0])}
        ).status_code
        == 400
    )


def test_verification_smtp_unavailable(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    h, _ = account()
    assert client.post("/api/auth/send-verification", headers=h).status_code == 503


def test_family_invitation_consent_and_private_scan_isolation(monkeypatch):
    messages = capture_mail(monkeypatch)
    owner, owner_email, owner_id = verified_account()
    member, email, uid = verified_account()
    stranger, _, _ = verified_account()
    g = client.post(
        "/api/families", headers=owner, json={"name": "Trusted people"}
    ).json()["id"]
    assert client.get(f"/api/families/{g}", headers=member).status_code == 404
    assert (
        client.post(
            f"/api/families/{g}/invitations", headers=member, json={"email": email}
        ).status_code
        == 404
    )
    r = client.post(
        f"/api/families/{g}/invitations", headers=owner, json={"email": email}
    )
    assert r.status_code == 201
    token = token_from(messages[-1], "invitation")
    assert (
        client.post(
            "/api/families/invitations/accept", headers=stranger, json={"token": token}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/families/invitations/preview", headers=member, json={"token": token}
        ).json()["group_name"]
        == "Trusted people"
    )
    assert (
        client.post(
            "/api/families/invitations/accept", headers=member, json={"token": token}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/families/invitations/accept", headers=member, json={"token": token}
        ).status_code
        == 404
    )
    result = client.post(
        "/api/scans/message",
        headers=member,
        json={
            "content": "PRIVATE SENTENCE. Send your OTP to receive a refund immediately."
        },
    ).json()
    sid = result["id"]
    assert (
        client.post(
            f"/api/families/{g}/alerts", headers=member, json={"scan_id": sid}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/families/{g}/alerts",
            headers=owner,
            json={"scan_id": sid, "consent": True},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/families/{g}/alerts",
            headers=member,
            json={"scan_id": sid, "consent": True},
        ).status_code
        == 201
    )
    shared = client.get(f"/api/families/{g}", headers=owner)
    assert (
        "PRIVATE SENTENCE" not in shared.text
        and "content" not in shared.text
        and "scan_id" not in shared.text
    )
    assert client.get(f"/api/history/{sid}", headers=owner).status_code == 404
    assert (
        client.delete(f"/api/families/{g}/members/{uid}", headers=member).status_code
        == 200
    )
    assert client.get(f"/api/families/{g}", headers=member).status_code == 404
    assert client.get(f"/api/families/{g}", headers=owner).json()["alerts"] == []
    assert client.delete(f"/api/families/{g}", headers=stranger).status_code == 404
    assert client.delete(f"/api/families/{g}", headers=owner).status_code == 200


def test_revoked_invitation_and_nonowner_management(monkeypatch):
    messages = capture_mail(monkeypatch)
    owner, _, _ = verified_account()
    guest, email, _ = verified_account()
    g = client.post("/api/families", headers=owner, json={"name": "My family"}).json()[
        "id"
    ]
    invitation = client.post(
        f"/api/families/{g}/invitations", headers=owner, json={"email": email}
    ).json()["id"]
    raw = token_from(messages[-1], "invitation")
    assert (
        client.delete(
            f"/api/families/{g}/invitations/{invitation}", headers=owner
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/families/invitations/accept", headers=guest, json={"token": raw}
        ).status_code
        == 404
    )


def test_preferences_and_optional_verification_gate(monkeypatch):
    h, _ = account()
    assert client.put(
        "/api/profile/preferences", headers=h, json={"language": "mr"}
    ).json() == {"language": "mr"}
    assert client.get("/api/profile/preferences", headers=h).json()["language"] == "mr"
    assert (
        client.put(
            "/api/profile/preferences", headers=h, json={"language": "xx"}
        ).status_code
        == 422
    )
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    assert (
        client.post(
            "/api/scans/url", headers=h, json={"content": "https://example.com"}
        ).status_code
        == 403
    )
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.get("/api/profile/preferences", headers=h).status_code == 200


def test_worker_production_fail_closed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SCANNER_WORKER_URL", raising=False)
    with pytest.raises(HTTPException) as error:
        worker_client.scan_in_worker("code", zipped(), "application/zip")
    assert error.value.status_code == 503


def test_worker_real_subprocess_qr_and_rejected_auth(monkeypatch):
    from backend.app.worker import app

    monkeypatch.setenv("SCANNER_WORKER_KEY", "test-worker-key-" + secrets.token_hex(20))
    with TestClient(app) as worker:
        assert worker.post("/scan/qr", content=b"bad").status_code == 401
        r = worker.post(
            "/scan/qr",
            content=qr_png("https://example.com"),
            headers={
                "X-Worker-Key": __import__("os").environ["SCANNER_WORKER_KEY"],
                "Content-Type": "image/png",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["result"]["details"]["qr_payload"] == "https://example.com"
        assert (
            worker.post(
                "/scan/code",
                content=b"not a zip",
                headers={
                    "X-Worker-Key": __import__("os").environ["SCANNER_WORKER_KEY"],
                    "Content-Type": "application/zip",
                },
            ).status_code
            == 422
        )


def test_worker_bad_configuration(monkeypatch):
    monkeypatch.setenv("SCANNER_WORKER_URL", "https://worker.invalid")
    monkeypatch.setenv("SCANNER_WORKER_KEY", "short")
    with pytest.raises(HTTPException) as error:
        worker_client.scan_in_worker("code", zipped(), "application/zip")
    assert error.value.status_code == 503


def test_worker_timeout_kills_process_group(monkeypatch):
    import asyncio
    from backend.app import worker

    class Process:
        pid = 987654

        async def communicate(self, body):
            return b"", b""

        async def wait(self):
            return -9

    async def create(*args, **kwargs):
        assert "SCANNER_WORKER_KEY" not in kwargs["env"]
        return Process()

    async def timeout(task, timeout):
        task.close()
        raise asyncio.TimeoutError()

    killed = []
    monkeypatch.setenv("SCANNER_WORKER_KEY", "a" * 40)
    monkeypatch.setattr(worker.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(worker.asyncio, "wait_for", timeout)
    monkeypatch.setattr(worker.os, "killpg", lambda pid, sig: killed.append(pid))
    with TestClient(worker.app) as gateway:
        response = gateway.post(
            "/scan/code", content=b"zip", headers={"X-Worker-Key": "a" * 40}
        )
    assert response.status_code == 503
    assert killed == [987654]


def test_worker_health_requires_secret(monkeypatch):
    from backend.app.worker import app

    monkeypatch.setenv("SCANNER_WORKER_KEY", "b" * 40)
    with TestClient(app) as gateway:
        assert gateway.get("/health").status_code == 401
        response = gateway.get("/health", headers={"X-Worker-Key": "b" * 40})
        assert response.status_code == 200
        assert isinstance(response.json()["voice_model_installed"], bool)
