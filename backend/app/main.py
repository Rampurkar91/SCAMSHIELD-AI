import os, secrets, hashlib, smtplib, csv, io, time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from typing import Literal
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Depends, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from reportlab.pdfgen import canvas
from .database import Base, engine, SessionLocal, User, Scan, Report, ResetToken
from .engine import analyze

SECRET = os.getenv("JWT_SECRET_KEY")
if not SECRET:
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("JWT_SECRET_KEY is required")
    SECRET = secrets.token_hex(32)
    print("Development: ephemeral JWT key; sessions expire on restart.")
if os.getenv("APP_ENV") != "production":
    Base.metadata.create_all(engine)
app = FastAPI(title="ScamShield AI", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
ph = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
buckets = defaultdict(deque)
auth_buckets = defaultdict(deque)


@app.middleware("http")
async def protect(request: Request, call_next):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    if len(buckets) > 10000:
        for old in list(buckets):
            if not buckets[old] or buckets[old][-1] < now - 60:
                del buckets[old]
    # File routes have their own streamed size bounds; JSON requests stay at 64 KiB.
    upload_paths = {
        "/api/scans/image",
        "/api/scans/qr",
        "/api/scans/code",
        "/api/scans/voice",
        "/api/scans/email-file",
    }
    limit = 9 * 1024 * 1024 if request.url.path in upload_paths else 65536
    try:
        body_length = int(request.headers.get("content-length", "0"))
    except ValueError:
        body_length = limit + 1
    if body_length > limit:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            {"detail": "Request exceeds the permitted size limit."}, status_code=413
        )
    # Bound chunked bodies too, before multipart parsing can spool unbounded input.
    if request.method in ("POST", "PUT", "PATCH"):
        buffered = bytearray()
        async for chunk in request.stream():
            buffered.extend(chunk)
            if len(buffered) > limit:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    {"detail": "Request exceeds the permitted size limit."},
                    status_code=413,
                )
        request._body = bytes(buffered)
    if request.method == "POST" and request.url.path.startswith("/api/auth/"):
        aq = auth_buckets[key]
        while aq and aq[0] < now - 60:
            aq.popleft()
        if len(aq) >= 15:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "Too many account attempts. Try again in a minute."},
                status_code=429,
            )
        aq.append(now)
    q = buckets[key]
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= 120:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            {"detail": "Too many requests; try again in a minute."}, status_code=429
        )
    q.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def db():
    with SessionLocal() as session:
        yield session


def current(
    request: Request,
    auth: HTTPAuthorizationCredentials = Depends(bearer),
    session=Depends(db),
):
    try:
        if not auth:
            raise ValueError()
        data = jwt.decode(auth.credentials, SECRET, algorithms=["HS256"])
        user = session.get(User, int(data["sub"]))
        if not user or data["v"] != user.version:
            raise ValueError()
        if os.getenv(
            "REQUIRE_EMAIL_VERIFICATION", "false"
        ).lower() == "true" and not request.url.path.startswith(
            ("/api/auth/", "/api/profile")
        ):
            from .services.family import is_verified

            if not is_verified(session, user.id):
                raise HTTPException(403, "Verify your email before using this feature.")
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Session expired. Please log in.")


def public(user):
    from .services.family import is_verified

    with SessionLocal() as session:
        verified = is_verified(session, user.id)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "email_verified": verified,
    }


def token(user):
    return jwt.encode(
        {
            "sub": str(user.id),
            "v": user.version,
            "exp": datetime.now(timezone.utc)
            + timedelta(
                minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
            ),
        },
        SECRET,
        algorithm="HS256",
    )


def verify(password, hashed):
    try:
        return ph.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Name must contain at least two non-space characters.")
        return value.strip()


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class Submission(BaseModel):
    content: str = Field(min_length=3, max_length=12000)
    use_external: bool = False
    use_ai: bool = False
    language: Literal["English", "Hindi", "Marathi"] = "English"


class Profile(BaseModel):
    name: str = Field(min_length=2, max_length=80)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Name must contain at least two non-space characters.")
        return value.strip()


class Password(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class Forgot(BaseModel):
    email: EmailStr


class Reset(BaseModel):
    token: str
    password: str = Field(min_length=12, max_length=128)


class ReportIn(BaseModel):
    category: Literal["URL", "Message", "UPI", "Email", "Phone", "Other"]
    description: str = Field(min_length=10, max_length=4000)


class StatusIn(BaseModel):
    status: Literal[
        "Submitted", "Under Review", "Confirmed Threat", "Not Verified", "Resolved"
    ]


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/auth/register", status_code=201)
def register(data: Register, session=Depends(db)):
    user = User(
        name=data.name.strip(),
        email=str(data.email).lower(),
        password=ph.hash(data.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "This email is already registered.")
    return {"token": token(user), "user": public(user)}


@app.post("/api/auth/login")
def login(data: Login, session=Depends(db)):
    user = session.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or not verify(data.password, user.password):
        raise HTTPException(401, "Invalid email or password.")
    return {"token": token(user), "user": public(user)}


@app.get("/api/profile")
@app.get("/api/auth/me")
def me(user=Depends(current)):
    return public(user)


@app.post("/api/auth/logout")
def logout(user=Depends(current), session=Depends(db)):
    user.version += 1
    session.commit()
    return {"message": "All sessions signed out."}


@app.put("/api/profile")
def profile(data: Profile, user=Depends(current), session=Depends(db)):
    user.name = data.name.strip()
    session.commit()
    return public(user)


@app.put("/api/profile/password")
def password(data: Password, user=Depends(current), session=Depends(db)):
    if not verify(data.current_password, user.password):
        raise HTTPException(400, "Current password is incorrect.")
    user.password = ph.hash(data.new_password)
    user.version += 1
    session.commit()
    return {"message": "Password changed. Please log in again."}


@app.post("/api/auth/forgot-password")
def forgot(data: Forgot, session=Depends(db)):
    if not os.getenv("SMTP_HOST") or not (
        os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM")
    ):
        raise HTTPException(
            503, "Password reset email is not configured. Contact the administrator."
        )
    if os.getenv("SMTP_USERNAME") and not os.getenv("SMTP_PASSWORD"):
        raise HTTPException(503, "SMTP authentication is not fully configured.")
    user = session.scalar(select(User).where(User.email == str(data.email).lower()))
    if user:
        raw = secrets.token_urlsafe(32)
        session.execute(delete(ResetToken).where(ResetToken.user_id == user.id))
        session.add(
            ResetToken(
                digest=hashlib.sha256(raw.encode()).hexdigest(),
                user_id=user.id,
                expires=datetime.now(timezone.utc) + timedelta(minutes=20),
            )
        )
        msg = EmailMessage()
        msg["Subject"] = "Reset your ScamShield password"
        msg["From"] = os.getenv("SMTP_FROM_EMAIL") or os.environ["SMTP_FROM"]
        msg["To"] = user.email
        msg.set_content(
            os.getenv("FRONTEND_URL", "http://localhost:5173")
            + "/reset-password?token="
            + raw
            + "\nThis single-use link expires in 20 minutes."
        )
        try:
            with smtplib.SMTP(
                os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=10
            ) as smtp:
                smtp.starttls()
                if os.getenv("SMTP_USERNAME"):
                    smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException, ValueError):
            raise HTTPException(503, "Email delivery is unavailable. Please try later.")
        session.commit()
    return {"message": "If the account exists, a reset link has been sent."}


@app.post("/api/auth/reset-password")
def reset(data: Reset, session=Depends(db)):
    record = session.scalar(
        select(ResetToken)
        .where(ResetToken.digest == hashlib.sha256(data.token.encode()).hexdigest())
        .with_for_update()
    )
    if not record or record.expires.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    ):
        raise HTTPException(400, "Invalid or expired reset link.")
    user = session.get(User, record.user_id)
    user.password = ph.hash(data.password)
    user.version += 1
    session.delete(record)
    session.commit()
    return {"message": "Password reset. You can now log in."}


def scan_dict(scan):
    return {
        "id": scan.id,
        "kind": scan.kind,
        "content": scan.content,
        "score": scan.score,
        "result": scan.result,
        "created_at": scan.created_at,
    }


from .services.routes import make_router, save_scan
from .services.analysis import enrich

app.include_router(make_router(current, db))
from .services.family import make_family_router

app.include_router(make_family_router(current, db))


@app.post("/api/scans/{kind}", status_code=201)
def scan(
    kind: Literal["url", "message", "upi", "email"],
    data: Submission,
    user=Depends(current),
    session=Depends(db),
):
    try:
        result = enrich(
            kind, data.content, data.use_external, data.use_ai, data.language
        )
    except ValueError as error:
        raise HTTPException(422, str(error))
    return save_scan(session, user, kind, data.content, result)


def owned(scan_id, user, session):
    record = session.get(Scan, scan_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Scan not found.")
    return record


@app.get("/api/history")
def history(
    q: str = "",
    kind: str = "",
    level: str = "",
    page: int = 1,
    user=Depends(current),
    session=Depends(db),
):
    records = session.scalars(
        select(Scan).where(Scan.user_id == user.id).order_by(Scan.id.desc())
    ).all()
    records = [
        r
        for r in records
        if (not q or q.lower() in r.content.lower())
        and (not kind or kind == r.kind)
        and (not level or level == r.result["level"])
    ]
    start = (max(1, page) - 1) * 20
    return {
        "total": len(records),
        "items": [scan_dict(r) for r in records[start : start + 20]],
    }


@app.get("/api/history/export.csv")
def csv_export(user=Depends(current), session=Depends(db)):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["ID", "Type", "Date", "Risk score", "Level"])
    for r in session.scalars(select(Scan).where(Scan.user_id == user.id)):
        writer.writerow([r.id, r.kind, r.created_at, r.score, r.result["level"]])
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="scamshield-history.csv"'
        },
    )


@app.get("/api/history/{scan_id}")
def detail(scan_id: int, user=Depends(current), session=Depends(db)):
    return scan_dict(owned(scan_id, user, session))


@app.delete("/api/history/{scan_id}")
def remove(scan_id: int, user=Depends(current), session=Depends(db)):
    session.delete(owned(scan_id, user, session))
    session.commit()
    return {"message": "Scan permanently deleted."}


@app.get("/api/history/{scan_id}/report.pdf")
def pdf(scan_id: int, user=Depends(current), session=Depends(db)):
    import textwrap

    r = owned(scan_id, user, session)
    out = io.BytesIO()
    c = canvas.Canvas(out)
    y = 790
    lines = (
        [
            "ScamShield AI | Security analysis",
            f"Scan #{r.id} | {r.kind.upper()} | {r.created_at}",
            f"Estimated risk: {r.score}/100 ({r.result['level']})",
            r.result["summary"],
        ]
        + [e["reason"] for e in r.result["indicators"]]
        + r.result["actions"]
        + r.result["limitations"]
    )
    for line in lines:
        for wrapped in textwrap.wrap(line, 88):
            if y < 60:
                c.showPage()
                y = 790
            c.drawString(40, y, wrapped)
            y -= 18
        y -= 10
    c.save()
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="scan-{r.id}.pdf"'},
    )


@app.get("/api/dashboard/analytics")
@app.get("/api/dashboard/overview")
def overview(user=Depends(current), session=Depends(db)):
    records = session.scalars(
        select(Scan).where(Scan.user_id == user.id).order_by(Scan.id.desc())
    ).all()
    today = datetime.now(timezone.utc).date()
    return {
        "total": len(records),
        "low": sum(r.score < 30 for r in records),
        "moderate": sum(30 <= r.score < 60 for r in records),
        "dangerous": sum(r.score >= 60 for r in records),
        "recent": [scan_dict(r) for r in records[:5]],
        "activity": [
            {
                "day": (today - timedelta(days=i)).strftime("%a"),
                "scans": sum(
                    r.created_at.date() == today - timedelta(days=i) for r in records
                ),
            }
            for i in reversed(range(7))
        ],
        "categories": [
            {"name": k.upper(), "value": sum(r.kind == k for r in records)}
            for k in ["url", "message", "upi", "email", "image", "qr", "voice", "code"]
        ],
    }


@app.post("/api/reports", status_code=201)
def report(data: ReportIn, user=Depends(current), session=Depends(db)):
    r = Report(user_id=user.id, **data.model_dump())
    session.add(r)
    session.commit()
    return {"id": r.id, "status": r.status}


@app.get("/api/reports")
def reports(user=Depends(current), session=Depends(db)):
    return session.scalars(
        select(Report).where(Report.user_id == user.id).order_by(Report.id.desc())
    ).all()


@app.get("/api/admin/reports")
def admin_reports(user=Depends(current), session=Depends(db)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required.")
    return session.scalars(select(Report).order_by(Report.id.desc())).all()


@app.put("/api/admin/reports/{report_id}")
def review(report_id: int, data: StatusIn, user=Depends(current), session=Depends(db)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required.")
    r = session.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found.")
    r.status = data.status
    session.commit()
    return {"id": r.id, "status": r.status}


# Production single-origin distribution. Disabled for API-only/local Vite setups.
if os.getenv("SERVE_FRONTEND", "false").lower() == "true":
    from .services.frontend import mount_frontend

    mount_frontend(app, os.getenv("FRONTEND_DIST", "frontend/dist"))
