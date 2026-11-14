# Implementation ledger

**A working phased release, not completion of every master-prompt requirement.** Existing features were preserved and expanded. No missing service is presented as having run.

| Feature | Actual implementation / API | Key files | Verification / outstanding configuration |
|---|---|---|---|
| Accounts and profile | Argon2, JWT, logout/password-change revocation, profile persistence | `backend/app/main.py`, `database.py`, `frontend/src/main.jsx` | Auth/profile/ownership tests, browser journey; 30-minute default JWT; email verification implemented (SMTP owner configuration required) |
| Password recovery | SMTP reset link, SHA-256 token digest, expiry, single use | same | Reset/expiry rejection/revocation and missing-SMTP tests; real SMTP delivery unverified |
| Core scans | `/api/scans/url`, `/message`, `/upi`, `/email`; transparent unique evidence, UPI action explanation | `engine.py`, `services/analysis.py` | Safe/suspicious/Indic/mixed-education regression tests; no destination fetched |
| Reputation adapters | Google Safe Browsing, PhishTank, URLhaus, optional VirusTotal, explicit opt-in | `integrations/providers.py` | Missing config, rate-limit, response validation/failure and score-floor tests with mocks; live credentials/egress needed |
| Gemini explanation and assistant | Official Google GenAI SDK, validated JSON, backend only, language selection, clear static fallback | `providers.py`, `services/routes.py`, `pages/Advanced.tsx` | Valid/invalid structured responses and fallback tests; real Gemini key/egress needed |
| SMS ML baseline | Trained UCI English TF-IDF + logistic regression; trusted cached artifact inference; separate from risk | `services/ml.py`, `scripts/train_models.py` | Trained/evaluated here, metrics committed, prediction test. Rebuild ignored model artifacts after fresh checkout |
| Email numeric baseline | UCI Spambase offline training/evaluation, not falsely applied to pasted email | training scripts, metadata | Trained/evaluated here; raw-email feature extractor not implemented |
| URL ML | Training command for licensed, multiclass user-supplied CSV | training scripts | No licensed training set validated; no trained URL classifier active |
| Image/OCR | JPEG/PNG/WebP, content/MIME/pixel/byte limits, timeout, Tesseract text extraction, no originals retained | `services/images.py`, upload UI | Real image validation; OCR success/failure mocked because Tesseract absent here. Docker installs OCR; not built here |
| QR | Real OpenCV QR decode, non-clickable payload, UPI intent | same | Actual generated UPI QR decoded and owned record persisted in Pytest; no camera integration |
| Email file | `/api/scans/email-file`; bounded .eml plain text/header extraction, attachment names/types only | `services/routes.py` | Email file API test; no attachment execution or independent SPF/DKIM verification |
| Voice | PCM WAV size/duration checks, explicit consent, optional local faster-whisper | `services/voice.py`, `routes.py`, upload UI | Consent/config tests and mocked local transcript pipeline; real model installation/inference unverified; no deepfake detector |
| Developer ZIP | Memory-only bounded ZIP text inspection, no extraction/execution; redacted findings with lines/remediation | `services/code.py` | Real ZIP scan, traversal/size rejects, secret-redaction tests. Built-in rules, not Semgrep/Bandit/Gitleaks |
| Public GitHub | Authorized public repo, fixed GitHub hosts, commit-pinned bounded archive, same static inspection | `services/github.py`, `pages/GitHubScanner.tsx` | Authorization/host validation tested; full live repository retrieval not verified; private repos unsupported |
| Dependency intelligence | Opt-in OSV for max 10 pinned PyPI/npm dependencies | `providers.py`, `code.py` | Failure handling covered; live OSV needs unrestricted outbound access; no fake key required |
| History/dashboard/export | Real persisted owned records, filters, pagination, PDF and CSV, Recharts | main API and main UI | Isolation/export/dashboard tests and browser journey; SQL aggregation at scale still needed |
| Critical notifications | Saved when score >=80, own list/mark-read | database, routes, Advanced UI | Critical scan creation and cross-user mark-read denied; no email notification delivery |
| Threat reports/admin | Owned reports, admin counts/review UI, provider config/outcome status without secrets | main API, routes, Advanced UI | Forbidden/non-admin and authorized status tests; attachments and audit trails pending |
| Learning | Two server-backed quizzes, saved attempts and explanations | routes, Advanced UI | Attempt persistence and isolation plus UI API tests; article content remains static |
| Shopkeeper mode | Large functional links to UPI, screenshot, QR and emergency workflow | Advanced UI | Compiles/typechecks; independent payment verification never claimed |
| Deployment | PostgreSQL SQLAlchemy support, two Alembic migrations, Docker/Compose, Render/Vercel config, `/health` DB probe | Dockerfiles, compose, migrations, render/vercel config | SQLite migration round-trip verified; no Docker/PostgreSQL/cloud deployment verified here |

## Database changes
Initial migration: users, scans (analysis/indicators JSON), reports, reset_tokens.
Second migration: notifications, quiz_attempts, security_api_logs (provider name/status/time only).
Not all 17 requested normalized tables exist. Unused placeholder tables were not added simply to imply implemented modules. Article/quiz definitions currently live in code; results/indicators live in scan JSON.

## Frontend language and TypeScript status
New advanced pages and shared security types use checked TypeScript. Existing tested core JSX is preserved; this is not a completed all-TypeScript conversion. AI/fallback responses can use English, Hindi or Marathi. English/Hindi/Marathi interface localization is now implemented; raw evidence and technical provider prose remain in their original language.

## Still outstanding
Separate marketing landing page; real-time camera QR; evidence/report attachments; account deletion/retention workflows; security audit logs; normalized result/indicator/profile tables; shared/distributed rate limits and provider budgets; container isolation deployment validation; validated deepfake detection; external static-scanner tool integrations; live SMTP/AI/reputation/OSV/PostgreSQL/deployment verification; URL ML training and deployment-grade evaluation.

The application should not be represented as production-audited or as a complete implementation of the master prompt.


## Verified family / localization / worker phase
Implemented consent-based family groups, SMTP email verification, persisted language preferences and English/Hindi/Marathi UI catalogs, production remote-scanner fail-closed behavior, hardened worker Compose configuration, model installation tooling and admin runtime diagnostics. See FAMILY_I18N_WORKER_SETUP.md for files, migrations, setup and remaining operator checks. Live SMTP/provider keys, model weights, Docker isolation and PostgreSQL deployment are not verified in this sandbox.

Validation for this phase: 47 backend tests and 20 frontend tests passed; TypeScript checks, production build and SQLite migration upgrade/downgrade/upgrade passed. Worker timeout kill and authenticated installation-health checks covered. Build retains a large-chunk performance warning. Optional faster-whisper package installed/imported locally; no speech model weights or live inference verified.

Browser smoke: registration, family verification gate, missing-SMTP error and Hindi locale switching passed. Preview uses a fresh migrated SQLite database; the earlier unversioned local development database was preserved, not forcibly stamped or overwritten. Existing unversioned deployments require a schema audit/baseline before migrations.
