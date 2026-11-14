"""Explicit opt-in integration check for an isolated, already-migrated test database.
Never run against customer/production data. Intended for the disposable CI database.
"""

import os
import uuid


def main():
    if os.getenv("ALLOW_DATABASE_SMOKE_TEST") != "true":
        raise SystemExit(
            "Requires ALLOW_DATABASE_SMOKE_TEST=true and an isolated test database."
        )
    from fastapi.testclient import TestClient
    from sqlalchemy import delete
    from ..app.main import app
    from ..app.database import SessionLocal, User, Scan, Notification

    uid = None
    try:
        with TestClient(app) as client:
            assert client.get("/health").json()["database"] == "connected"
            response = client.post(
                "/api/auth/register",
                json={
                    "name": "CI smoke account",
                    "email": f"ci-{uuid.uuid4().hex}@example.com",
                    "password": "Disposable smoke-test passphrase 123!",
                },
            )
            assert response.status_code == 201, response.text
            data = response.json()
            uid = data["user"]["id"]
            headers = {"Authorization": "Bearer " + data["token"]}
            response = client.post(
                "/api/scans/url",
                headers=headers,
                json={"content": "https://example.com/controlled-fixture"},
            )
            assert response.status_code == 201, response.text
            scan_id = response.json()["id"]
            assert (
                client.get(f"/api/history/{scan_id}", headers=headers).status_code
                == 200
            )
            assert client.get(f"/api/history/{scan_id}").status_code == 401
            assert (
                client.get("/api/dashboard/overview", headers=headers).json()["total"]
                == 1
            )
            assert client.get(
                f"/api/history/{scan_id}/report.pdf", headers=headers
            ).content.startswith(b"%PDF")
    finally:
        if uid is not None:
            with SessionLocal() as session:
                session.execute(delete(Notification).where(Notification.user_id == uid))
                session.execute(delete(Scan).where(Scan.user_id == uid))
                session.execute(delete(User).where(User.id == uid))
                session.commit()
    print("Database smoke journey passed.")


if __name__ == "__main__":
    main()
