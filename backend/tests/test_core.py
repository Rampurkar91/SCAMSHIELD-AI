import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.mkdtemp()) / "tests.db")
os.environ["JWT_SECRET_KEY"] = "test-only-secret-with-at-least-thirty-two-characters"
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, buckets, auth_buckets
from backend.app.engine import analyze

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_limit():
    buckets.clear()
    auth_buckets.clear()


def account(prefix="test"):
    import uuid

    email = f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Test Person",
            "email": email,
            "password": "A unique passphrase 123!",
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}, email


def test_auth_and_revocation():
    headers, email = account()
    assert client.get("/api/auth/me", headers=headers).json()["email"] == email
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": "bad"}
        ).status_code
        == 401
    )
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_validation():
    assert (
        client.post(
            "/api/auth/register", json={"name": "A", "email": "bad", "password": "weak"}
        ).status_code
        == 422
    )
    assert client.get("/api/history").status_code == 401


def test_scan_journey_and_ownership():
    headers, _ = account()
    other, _ = account()
    r = client.post(
        "/api/scans/url",
        headers=headers,
        json={
            "content": "http://paypal-verify.xyz/login?redirect=https://evil.example"
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["score"] >= 60
    id = data["id"]
    assert client.get("/api/history", headers=headers).json()["total"] == 1
    assert client.get(f"/api/history/{id}", headers=other).status_code == 404
    assert client.delete(f"/api/history/{id}", headers=other).status_code == 404
    assert client.get(f"/api/history/{id}/report.pdf", headers=other).status_code == 404
    pdf = client.get(f"/api/history/{id}/report.pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert str(id) in client.get("/api/history/export.csv", headers=headers).text
    assert client.get("/api/dashboard/overview", headers=headers).json()["total"] == 1
    assert client.delete(f"/api/history/{id}", headers=headers).status_code == 200
    assert client.get("/api/history", headers=headers).json()["total"] == 0


def test_scanner_validation():
    h, _ = account()
    for url in ["file:///etc/passwd", "not a url", "javascript:alert(1)"]:
        assert (
            client.post("/api/scans/url", headers=h, json={"content": url}).status_code
            == 422
        )
    assert (
        client.post(
            "/api/scans/voice", headers=h, json={"content": "example"}
        ).status_code
        == 422
    )


def test_message_and_upi():
    assert (
        analyze(
            "message",
            "Urgent! Your account will be blocked immediately. Send your OTP to verify KYC.",
        )["score"]
        >= 80
    )
    assert (
        analyze(
            "upi",
            "To receive your refund, enter your UPI PIN and approve collect request.",
        )["score"]
        >= 80
    )
    assert (
        analyze("message", "Never share your OTP or UPI PIN with anyone.")["score"] == 0
    )
    assert analyze("message", "Lunch at noon tomorrow?")["score"] == 0
    assert analyze("message", "तुरंत अपना ओटीपी भेजें। खाता बंद होगा।")["score"] > 0
    assert analyze("upi", "ताबडतोब पिन सांगा. खाते बंद होईल.")["score"] > 0


def test_url_limits_and_evidence():
    result = analyze("url", "https://google.com/search?q=hello")
    assert result["score"] == 0
    assert result["provider"]["status"] == "not_checked"
    assert analyze("url", "http://127.0.0.1/test")["score"] == 40
    assert analyze("url", "https://real.example@evil.example")["score"] == 30
    result = analyze("message", "Send your OTP https://bit.ly/one https://bit.ly/two")
    codes = [i["code"] for i in result["indicators"]]
    assert len(codes) == len(set(codes))
    assert 0 <= result["score"] <= 100


def test_email():
    r = analyze(
        "email",
        "From: Bank <stranger@example.com>\nAuthentication-Results: mx.example; spf=fail\nSubject: Account\n\nUrgent KYC blocked immediately. Send password.",
    )
    assert r["score"] >= 80
    assert "untrusted" in r["details"]["header_note"]


def test_reports_and_admin():
    h, _ = account()
    other, _ = account()
    r = client.post(
        "/api/reports",
        headers=h,
        json={"category": "UPI", "description": "An unknown person requested payment."},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "Submitted"
    assert client.get("/api/reports", headers=other).json() == []
    assert client.get("/api/admin/reports", headers=h).status_code == 403
    assert (
        client.put(
            "/api/admin/reports/1", headers=h, json={"status": "Confirmed Threat"}
        ).status_code
        == 403
    )


def test_profile_and_change_password():
    h, email = account()
    assert (
        client.put("/api/profile", headers=h, json={"name": "Updated Name"}).json()[
            "name"
        ]
        == "Updated Name"
    )
    assert (
        client.put(
            "/api/profile/password",
            headers=h,
            json={
                "current_password": "wrong",
                "new_password": "another strong passphrase",
            },
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/profile/password",
            headers=h,
            json={
                "current_password": "A unique passphrase 123!",
                "new_password": "another strong passphrase",
            },
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"email": email, "password": "another strong passphrase"},
        ).status_code
        == 200
    )


def test_reset_unconfigured_and_invalid():
    assert (
        client.post(
            "/api/auth/forgot-password", json={"email": "nobody@example.com"}
        ).status_code
        == 503
    )
    assert (
        client.post(
            "/api/auth/reset-password",
            json={"token": "bad", "password": "new safe passphrase"},
        ).status_code
        == 400
    )


def test_reset_single_use(monkeypatch):
    from backend.app.database import SessionLocal, ResetToken, User
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta
    import hashlib

    h, email = account()
    raw = "random-test-only-token"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        db.add(
            ResetToken(
                digest=hashlib.sha256(raw.encode()).hexdigest(),
                user_id=user.id,
                expires=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        )
        db.commit()
    payload = {"token": raw, "password": "reset new passphrase 123"}
    assert client.post("/api/auth/reset-password", json=payload).status_code == 200
    assert client.post("/api/auth/reset-password", json=payload).status_code == 400
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": email, "password": payload["password"]}
        ).status_code
        == 200
    )


def test_rate_limit():
    responses = [client.get("/api/health") for _ in range(121)]
    assert responses[-1].status_code == 429


def test_auth_throttle():
    results = [
        client.post(
            "/api/auth/login", json={"email": "no@example.com", "password": "bad"}
        )
        for _ in range(16)
    ]
    assert results[-1].status_code == 429


def test_request_size_limit():
    assert client.post("/api/auth/login", content="x" * 70000).status_code == 413


def test_education_sentence_cannot_hide_second_request():
    r = analyze(
        "message", "Never share your OTP. Send your password to our agent immediately."
    )
    assert any(i["code"] == "secret_request" for i in r["indicators"])
    assert analyze("message", "ओटीपी किंवा पिन शेअर करू नका.")["score"] == 0


def test_upi_action_and_url_syntax():
    assert (
        "collect"
        in analyze("upi", "Approve this collect request now")["details"][
            "payment_action"
        ]
    )
    with pytest.raises(ValueError):
        analyze("url", "https://example.com:invalid")
    with pytest.raises(ValueError):
        analyze("url", "https://example .com/path")
