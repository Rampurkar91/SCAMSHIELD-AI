# ScamShield AI
### Intelligent UPI Fraud, Phishing & Cyber Threat Detection Platform

Cyber-safety application for **VibeX Codes — Track 3**, helping citizens, families and shopkeepers pause before acting on suspicious content.

**Status: a working phased implementation, not completion of every feature in the master specification or a production-audited service.** Code, tests, migrations and deployment configuration are in this repository. See the [feature ledger](docs/PROGRESS.md) for exact implementation/verification status.

## Implemented
- Responsive dark security workspace, registration/login/profile/password screens and database-backed dashboard.
- Argon2 passwords, JWT expiry, all-session revocation on logout/password change, SMTP-backed hashed single-use password reset.
- Explainable local URL, message, UPI and email analysis, extracted non-clickable links and payment-action interpretation.
- Optional, explicitly consented backend adapters for Google Safe Browsing, PhishTank, URLhaus, VirusTotal and Gemini (official Google GenAI SDK).
- Gemini cybersecurity assistant with English/Hindi/Marathi response selection and clearly labeled static fallback when unavailable. Chat is not stored in the database.
- Real OpenCV QR decoding, UPI URI intent, Tesseract OCR integration and image validation. OCR needs installed software.
- Plain-text .eml parsing, attachment-name listing (no execution), optional local WAV/Whisper transcript analysis with consent. No voice deepfake detection claim.
- Bounded source-ZIP and public GitHub static inspection; redacted findings with file/line/remediation. Optional OSV dependency lookup. No arbitrary code execution, archive extraction or git hooks.
- Owned history/search/filter/pagination/deletion, PDF/CSV reports, dashboard charts, saved critical notifications and quiz scores.
- Threat reports and administrator review/configuration-status UI with real persisted provider outcomes and no secret exposure.
- Simplified shopkeeper page, awareness content and emergency guide for **1930** and https://cybercrime.gov.in/.
- Reproducible dataset download/preprocessing/training scripts; actual trained/evaluated SMS and Spambase baselines, committed provenance and metrics.

## Honest limits
Missing credentials return unavailable/error statuses, not invented provider results. This sandbox cannot verify live AI, reputation or OSV calls. Tesseract and a speech model are not installed here; OCR/transcription pipelines have mocked success tests and explicit missing-software errors. QR decoding, local rule scans, static ZIP scans, datasets and baseline training ran locally.

Still pending: family invitations/consent groups, email verification, full Hindi/Marathi UI translation, all-TypeScript migration, standalone marketing landing page, camera QR, evidence attachments, audit trails/retention/account deletion, full normalized 17-table schema, Semgrep/Bandit/Gitleaks, dedicated resource-isolated workers, distributed quotas, deployment-grade URL ML and live PostgreSQL/cloud verification. New advanced pages/types use TypeScript; existing core JSX is preserved.

## Quick start
Requires Python 3.11+ and Node 22.12+.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm --prefix frontend ci
# Terminal 1 (repository root):
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# Terminal 2:
npm --prefix frontend run dev -- --port 5173
```
Open http://localhost:5173. Register your own account. No demo credentials or synthetic analytics are seeded. SQLite is the local fallback; the deployment database is PostgreSQL. The Vite proxy keeps browser calls relative to `/api`, including remote previews.

Copy `backend/.env.example` to `backend/.env` if configuring PostgreSQL, SMTP, tools or providers; the backend loads it automatically. It contains placeholders only. **Do not copy the example PostgreSQL URL unchanged and expect connectivity.** Omit `DATABASE_URL` for local SQLite. Without a JWT key, development creates an ephemeral random key; restarting invalidates sessions. Production requires a persistent secret.

### PostgreSQL
```bash
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/scamshield'
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
alembic upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
Production disables startup schema creation. Run Alembic first. Existing exact phase-one development schemas created by startup DDL may be stamped to `9ff54a7fbd93` then upgraded; do not stamp unrelated schemas. Back up before migration. Local development can auto-create new tables, but production migration paths must be used in deployments.

## Train real baselines
```bash
.venv/bin/python -m backend.scripts.download_datasets all
.venv/bin/python -m backend.scripts.train_models sms
.venv/bin/python -m backend.scripts.train_models email
# URL research training requires your own licensed multiclass CSV:
.venv/bin/python -m backend.scripts.train_models url --input /path/to/licensed-urls.csv
```
Raw data and trusted `.joblib` artifacts are intentionally ignored by Git; rebuild on a fresh checkout. Source hashes, Git blob versions, attribution/license references, held-out metrics and confusion matrices are committed in `backend/datasets/metadata/`. In this sandbox a system CA bundle was needed: prefix the download command with `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` if appropriate for your network. Never disable certificate verification.

Measured SMS accuracy **97.68%**, spam F1 **90.91%**; Spambase accuracy **93.59%**, spam F1 **92.08%**. These are fixed random-split spam metrics, **not calibrated fraud probabilities**. Only the English SMS artifact supplies an advisory label at runtime. Spambase requires 57 numeric features and is offline-only, not falsely applied to pasted raw email. No URL ML model was trained. See [datasets and limitations](docs/datasets.md).

## Documentation
- [API and dataset setup guide](docs/API_AND_DATASET_SETUP.md): registration links, key variables, consent, quotas, missing-config behavior, OCR/voice installation and exact training commands.
- [Feature/file/API/database/test ledger](docs/PROGRESS.md).
- [Architecture and workflow diagrams](docs/ARCHITECTURE.md).
- [Deployment: Docker Compose, Render, Vercel, PostgreSQL](docs/deployment.md).
- [Tests and safe hackathon demo](docs/testing.md).

## Project layout
```
backend/app/database.py          ORM models and sessions
backend/app/engine.py            Local transparent scoring
backend/app/main.py              Core auth/history/dashboard/report API
backend/app/integrations/        Fixed-endpoint provider clients
backend/app/services/            Analysis, ML, image, voice, code, GitHub and advanced routes
backend/migrations/              Two Alembic schema revisions
backend/scripts/                Reproducible downloads and offline training
backend/datasets/metadata/       Provenance and measured evaluations
backend/tests/                  API, rule, file, provider and isolation tests
frontend/src/main.jsx            Preserved core routed application
frontend/src/pages/              TypeScript advanced scanner/admin/assistant/learning pages
frontend/src/types/              Checked security-domain types
frontend/e2e/                   Browser journeys
```

## Main API
Interactive schema: http://localhost:8000/docs. Protected endpoints require `Authorization: Bearer <token>`.
- Auth: POST `/api/auth/register`, `/login`, `/logout`, `/forgot-password`, `/reset-password`; GET `/api/auth/me`.
- Profile: GET/PUT `/api/profile`, PUT `/api/profile/password`.
- Text scans: POST `/api/scans/{url,message,upi,email}` with `{content,use_external:false,use_ai:false}`.
- Multipart files: POST `/api/scans/{image,qr,code,voice,email-file}` using `file`; voice requires `consent=true`, code optionally `check_dependencies=true`.
- Public source: POST `/api/scans/github` with `{url,authorized:true,check_dependencies:false}`.
- AI: POST `/api/assistant/chat` with `{message,language:"English",use_ai:false,context:[]}`.
- History: GET `/api/history?q=&kind=&level=&page=1`; GET/DELETE `/api/history/{id}`; GET `/api/history/{id}/report.pdf` and `/api/history/export.csv`.
- Dashboard: GET `/api/dashboard/overview` and `/analytics`.
- Reports: POST/GET `/api/reports`; admin GET `/api/admin/reports`, PUT `/api/admin/reports/{id}`.
- Notifications: GET `/api/notifications`, PUT `/api/notifications/{id}/read`.
- Learning: GET `/api/awareness/quizzes`, POST `/api/awareness/quizzes/{id}/submit` with `{answer:0}`.
- Admin: GET `/api/admin/dashboard`, `/api/admin/integrations/status`.
- Health: GET `/health` probes the database and reports configured integrations; `/api/health` is a simple process liveness check.

Provision administrators only through a trusted operator/database console by setting `users.role=admin`. No self-promotion endpoint or default admin password exists. Reports start as Submitted, never automatically as confirmed threats.

## Risk semantics
0–29 low, 30–59 moderate, 60–79 high, 80–100 critical. The engine deduplicates weighted local evidence. A real provider match establishes a minimum score of 90; ML labels and AI prose remain separate advisory sources. Static source scans use highest finding severity, not the number of duplicate lines. All scores are risk estimates, not fraud probabilities. Low risk is **not** proof of safety; HTTPS does not establish legitimacy. URLs are never automatically opened. Screenshots/messages do not verify bank transactions.

## Tests
```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
# Start both servers, install Playwright Chromium, then:
npm --prefix frontend run test:e2e
```
See [testing notes](docs/testing.md) for exact browser installation, dependency audits, coverage, mock boundaries and demo instructions. No Docker/PostgreSQL/cloud, real SMTP, real speech inference or live external-provider verification is claimed.

## Security / production blockers
Passwords are Argon2-hashed; reset tokens are hashed, expiring and single-use. All scan/export/report/notification/quiz routes enforce user ownership; admin routes enforce roles. Inputs and provider JSON are untrusted, React renders text, and no submitted code or attachments execute. Bodies are bounded before multipart parsing, and image/ZIP/audio processors apply further caps. No submitted URL is fetched; provider hosts are fixed. Public GitHub retrieval is commit-pinned and size-limited.

API tokens live in sessionStorage (not localStorage), expire after a configurable 30 minutes by default, and are revoked by account version. A hardened production cookie/session strategy still needs evaluation. Rate limits are in-memory per IP, not distributed. External-provider budgets are not globally enforced. OCR/voice run on bounded inputs in threads, not isolated OS workers. Add resource-isolated workers, shared quotas and an egress gateway before unrestricted public use.

Submitted text/results are stored without application-layer encryption until user deletion. Use managed encryption at rest, least-privilege database credentials and encrypted backups; never submit secrets. Report deletion/account deletion/automated retention/audit trails are pending. History and analytics currently materialize owned records; replace with SQL aggregates and bounded query pagination before large-scale use. PDF exports use standard fonts, so Indic font embedding remains pending. Obtain a professional security review before public production deployment.
