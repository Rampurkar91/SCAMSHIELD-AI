import os, shutil
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from ..database import Scan, User, Notification, IntegrationEvent, QuizAttempt
from ..engine import analyze
from ..integrations.providers import configured, gemini_answer
from .images import analyze_image
from .code import scan_zip
from .voice import analyze_voice
from .worker_client import scan_in_worker

QUIZZES = [
    {
        "id": "upi-pin",
        "question": "A caller asks for your UPI PIN to send a refund. What should you do?",
        "options": ["Enter the PIN", "Decline and verify through the official app"],
        "correct": 1,
        "explanation": "A UPI PIN normally authorizes an outgoing payment, not receipt of money.",
    },
    {
        "id": "https",
        "question": "Does HTTPS prove a website is trustworthy?",
        "options": ["Yes", "No, it encrypts traffic but cannot establish legitimacy"],
        "correct": 1,
        "explanation": "Attackers can also obtain HTTPS certificates.",
    },
]


class ChatIn(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    language: Literal["English", "Hindi", "Marathi"] = "English"
    use_ai: bool = False
    context: list[str] = Field(default_factory=list, max_length=6)


class GitHubIn(BaseModel):
    url: str = Field(max_length=300)
    authorized: bool = False
    check_dependencies: bool = False


class QuizIn(BaseModel):
    answer: int = Field(ge=0, le=1)


def save_scan(session, user, kind, content, result):
    record = Scan(
        user_id=user.id,
        kind=kind,
        content=content[:12000],
        score=result["score"],
        result=result,
    )
    session.add(record)
    session.flush()
    if result["score"] >= 80:
        session.add(
            Notification(
                user_id=user.id,
                message=f"Critical risk indicators in scan #{record.id}. Review the analysis before acting.",
            )
        )
    for p in result.get("providers", []):
        session.add(IntegrationEvent(provider=p["provider"], status=p["status"]))
    if result.get("ai", {}).get("status") not in (None, "not_requested"):
        session.add(IntegrationEvent(provider="gemini", status=result["ai"]["status"]))
    session.commit()
    return {
        "id": record.id,
        "kind": record.kind,
        "content": record.content,
        "score": record.score,
        "result": record.result,
        "created_at": record.created_at,
    }


def make_router(current, db):
    router = APIRouter()

    def admin(user=Depends(current)):
        if user.role != "admin":
            raise HTTPException(403, "Administrator access required.")
        return user

    async def read_file(file, limit):
        data = bytearray()
        try:
            while chunk := await file.read(65536):
                data.extend(chunk)
                if len(data) > limit:
                    raise HTTPException(413, "Upload exceeds the permitted file size.")
        finally:
            await file.close()
        return bytes(data)

    @router.get("/health")
    def health(session=Depends(db)):
        try:
            session.execute(text("SELECT 1"))
        except Exception:
            raise HTTPException(503, "Database unavailable.")
        return {
            "status": "ok",
            "database": "connected",
            "integrations": {
                p["name"]: "configured_not_probed"
                if p["configured"]
                else "not_configured"
                for p in configured()
            },
            "ocr_installed": bool(
                shutil.which(os.getenv("TESSERACT_CMD") or "tesseract")
            ),
        }

    @router.post("/api/scans/image", status_code=201)
    @router.post("/api/scans/qr", status_code=201)
    async def image(
        request: Request,
        file: UploadFile = File(...),
        mode: Literal["image", "qr"] = Form("image"),
        user=Depends(current),
        session=Depends(db),
    ):
        raw = await read_file(file, 5 * 1024 * 1024)
        from starlette.concurrency import run_in_threadpool

        mode = "qr" if request.url.path.endswith("/qr") else mode
        content, result = await run_in_threadpool(
            scan_in_worker, mode, raw, file.content_type
        )
        return save_scan(session, user, mode, content, result)

    @router.post("/api/scans/code", status_code=201)
    async def code(
        file: UploadFile = File(...),
        check_dependencies: bool = Form(False),
        user=Depends(current),
        session=Depends(db),
    ):
        raw = await read_file(file, 5 * 1024 * 1024)
        from starlette.concurrency import run_in_threadpool

        content, result = await run_in_threadpool(
            scan_in_worker, "code", raw, file.content_type, check_dependencies
        )
        return save_scan(session, user, "code", content, result)

    @router.post("/api/scans/voice", status_code=201)
    async def voice(
        file: UploadFile = File(...),
        consent: bool = Form(False),
        user=Depends(current),
        session=Depends(db),
    ):
        if not consent:
            raise HTTPException(
                422, "Explicit consent to process this recording is required."
            )
        if file.content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
            raise HTTPException(415, "Only PCM WAV is supported.")
        raw = await read_file(file, 8 * 1024 * 1024)
        from starlette.concurrency import run_in_threadpool

        content, result = await run_in_threadpool(
            scan_in_worker, "voice", raw, file.content_type
        )
        return save_scan(session, user, "voice", content, result)

    @router.post("/api/scans/email-file", status_code=201)
    async def email_file(
        file: UploadFile = File(...), user=Depends(current), session=Depends(db)
    ):
        from email import policy
        from email.parser import BytesParser

        raw = await read_file(file, 512 * 1024)
        message = BytesParser(policy=policy.default).parsebytes(raw)
        body = message.get_body(preferencelist=("plain",))
        if body is None:
            raise HTTPException(
                422,
                "No plain text email body found. HTML and attachments are not executed or rendered.",
            )
        content = (
            "\n".join(
                f"{name}: {message.get(name, '')}"
                for name in ("From", "Subject", "Authentication-Results")
            )
            + "\n\n"
            + str(body.get_content())
        )
        if len(content) > 12000:
            raise HTTPException(413, "Email text exceeds 12,000 characters.")
        from .analysis import enrich

        result = enrich("email", content)
        result["details"]["attachments"] = [
            {
                "name": str(a.get_filename() or "unnamed")[:200],
                "content_type": a.get_content_type(),
            }
            for a in message.iter_attachments()
        ][:30]
        return save_scan(session, user, "email", content, result)

    @router.post("/api/scans/github", status_code=201)
    def github(data: GitHubIn, user=Depends(current), session=Depends(db)):
        if not data.authorized:
            raise HTTPException(
                422, "Confirm that you are authorized to review this public repository."
            )
        from .github import scan_github

        result = scan_github(data.url, data.check_dependencies)
        return save_scan(session, user, "code", "GitHub: " + data.url, result)

    @router.post("/api/assistant/chat")
    def chat(data: ChatIn, user=Depends(current), session=Depends(db)):
        if any(len(c) > 1000 for c in data.context):
            raise HTTPException(422, "Context entries must be at most 1000 characters.")
        result = (
            gemini_answer(data.message, data.language, data.context)
            if data.use_ai
            else {"status": "not_requested", "reason": "External AI was not requested."}
        )
        if data.use_ai:
            session.add(IntegrationEvent(provider="gemini", status=result["status"]))
            session.commit()
        if result["status"] != "ok":
            guidance = {
                "English": "Pause before acting. Never share an OTP, password or UPI PIN. Verify requests independently in your official banking app. If money was lost, contact your bank immediately, call 1930 and report at cybercrime.gov.in.",
                "Hindi": "रुकें और स्वतंत्र रूप से जाँच करें। ओटीपी, पासवर्ड या यूपीआई पिन साझा न करें। पैसे खोने पर तुरंत बैंक से संपर्क करें, 1930 पर कॉल करें और cybercrime.gov.in पर रिपोर्ट करें।",
                "Marathi": "थांबा आणि स्वतंत्रपणे पडताळणी करा. ओटीपी, पासवर्ड किंवा यूपीआय पिन शेअर करू नका. पैसे गमावल्यास लगेच बँकेशी संपर्क करा, 1930 वर कॉल करा आणि cybercrime.gov.in येथे तक्रार करा.",
            }
            return {
                **result,
                "source": "Static safety fallback, not an AI answer",
                "explanation": guidance[data.language],
                "actions": [],
                "uncertainty": "This fallback is general guidance, not contextual analysis. Conversation is not retained by ScamShield.",
            }
        return result

    @router.get("/api/notifications")
    def notifications(user=Depends(current), session=Depends(db)):
        return session.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(50)
        ).all()

    @router.put("/api/notifications/{notification_id}/read")
    def mark_read(notification_id: int, user=Depends(current), session=Depends(db)):
        item = session.get(Notification, notification_id)
        if not item or item.user_id != user.id:
            raise HTTPException(404, "Notification not found.")
        item.read = True
        session.commit()
        return {"message": "Marked as read."}

    @router.get("/api/awareness/quizzes")
    def quizzes(user=Depends(current), session=Depends(db)):
        return {
            "quizzes": [
                {k: v for k, v in q.items() if k not in ("correct", "explanation")}
                for q in QUIZZES
            ],
            "attempts": session.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user.id)
                .order_by(QuizAttempt.id.desc())
                .limit(20)
            ).all(),
        }

    @router.post("/api/awareness/quizzes/{quiz_id}/submit")
    def submit_quiz(
        quiz_id: str, data: QuizIn, user=Depends(current), session=Depends(db)
    ):
        quiz = next((q for q in QUIZZES if q["id"] == quiz_id), None)
        if not quiz:
            raise HTTPException(404, "Quiz not found.")
        score = 100 if data.answer == quiz["correct"] else 0
        session.add(QuizAttempt(user_id=user.id, quiz_id=quiz_id, score=score))
        session.commit()
        return {"score": score, "explanation": quiz["explanation"]}

    @router.get("/api/admin/runtime")
    def runtime(user=Depends(admin)):
        from .runtime_status import runtime_status

        return runtime_status()

    @router.get("/api/admin/integrations/status")
    def status(user=Depends(admin), session=Depends(db)):
        result = []
        for p in configured():
            last = session.scalar(
                select(IntegrationEvent)
                .where(IntegrationEvent.provider == p["name"])
                .order_by(IntegrationEvent.id.desc())
                .limit(1)
            )
            success = session.scalar(
                select(IntegrationEvent)
                .where(
                    IntegrationEvent.provider == p["name"],
                    IntegrationEvent.status.in_(
                        ["ok", "matched", "no_match", "not_found"]
                    ),
                )
                .order_by(IntegrationEvent.id.desc())
                .limit(1)
            )
            result.append(
                {
                    **p,
                    "availability": last.status if last else "not_checked",
                    "last_check": last.created_at if last else None,
                    "last_success": success.created_at if success else None,
                    "last_error": last.status
                    if last and last.status in ("error", "rate_limited")
                    else None,
                }
            )
        return result

    @router.get("/api/admin/dashboard")
    def admin_dashboard(user=Depends(admin), session=Depends(db)):
        from sqlalchemy import func
        from ..database import Report

        return {
            "users": session.scalar(select(func.count(User.id))),
            "scans": session.scalar(select(func.count(Scan.id))),
            "reports": session.scalar(select(func.count(Report.id))),
        }

    return router
