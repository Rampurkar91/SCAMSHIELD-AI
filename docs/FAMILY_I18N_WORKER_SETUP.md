# Verified family sharing, translations and scanner isolation

## Implemented workflows

- `backend/app/services/family.py`, `mailer.py`, `database.py`, migration
  `230f9fb85601`: hashed, expiring, single-use email verification; resend cooldown;
  verified-email family invitations with recipient-bound explicit acceptance;
  group ownership/membership checks; delete/leave/revoke; per-scan consent to
  share only kind/risk/time summaries. A family member cannot read another
  member's scan history, submitted content or original results. Sharing is not
  automatic. SMTP uses STARTTLS with certificate verification. Undeliverable
  mail produces an explicit error, not a successful fake response.
- `frontend/src/pages/Family.tsx`: email verification, group/invitation/member
  management and explicit summary sharing; routes in `main.jsx`.
- `frontend/src/i18n/`: English, Hindi and Marathi interface catalogs, language
  selector, translated host text/labels/confirmation dialogs/errors; saved local
  preference and authenticated `/api/profile/preferences` persistence. Babel
  source extraction and rendered-component tests guard catalog coverage.
  Submitted evidence, code, identifiers and backend enums are not rewritten.
  Technical scanner findings can remain in the original language; this is shown
  in the results UI. Optional AI explanation requests use the selected language.
  This is UI localization, not guaranteed translation of arbitrary provider prose.
- `worker.py`, `worker_task.py`, `services/worker_client.py`: authenticated remote
  worker; production fails closed without one. File processing, including GitHub
  archives, runs in a disposable subprocess with a 95-second deadline and process
  group termination. ZIP contents are inspected, never executed. Optional OSV
  requests happen in the API, not the offline worker. A subprocess alone is not a
  security boundary: deploy using the container/network restrictions below.
- Admin integration screen (`RuntimeSetup.tsx`, `/api/admin/runtime`) shows worker,
  OCR, speech model and SMTP configuration checks, never credential values.
  Installation checks do not certify a successful inference or email delivery.

## Local Docker setup

```bash
python backend/scripts/configure_local.py
# Configure backend/.env from backend/.env.example for SMTP and optional services.
# Keep root .env private: generated DB/JWT/worker secrets must never be committed.
docker compose --profile setup run --rm model-setup
docker compose up --build
```

The setup profile downloads an approved faster-whisper model before serving user
requests. The installer records a resolved model revision and provenance. This
requires operator internet access to Hugging Face, not available in this Arena
sandbox. Models/credentials are not committed. `requirements-voice.txt` pins the
installed faster-whisper version; download and dependency suitability must still
be reviewed for your environment. CPU transcription accepts PCM WAV, 1–120 seconds;
it is not AI-voice/deepfake detection.

The worker image installs Tesseract with English, Hindi and Marathi packs. Compose
runs UID 10001, read-only root, capped resources/processes, dropped capabilities,
no-new-privileges, temporary scratch storage and a read-only speech model volume.
The worker has only an internal network and no published port, database connection,
JWT, SMTP or provider credentials. The API can reach both worker and external
providers. Never attach the runtime worker to an outbound network to download a
model. Run the separate setup profile instead. Container resource settings must
be verified with your installed Docker/Compose version.

Set SMTP_HOST, SMTP_PORT (STARTTLS, normally 587), SMTP_USERNAME, SMTP_PASSWORD and
SMTP_FROM_EMAIL with your mail provider. Configure FRONTEND_URL to the exact public
frontend origin so verification links and CORS are correct. SMTP implicit TLS port
465 is not supported by this helper. Family sharing always requires verification;
REQUIRE_EMAIL_VERIFICATION=true additionally gates protected scanning features.

Provider credentials (Gemini, reputation services) remain owner-supplied backend
environment settings, documented in API_AND_DATASET_SETUP.md. The app does not
manufacture keys, claim unconfigured services are live, or upload content without
the associated user opt-in. Use admin diagnostics and real authorized samples to
verify configured services.

## Cloud deployment and operations

The Render API blueprint deliberately leaves binary scanning disabled until an
isolated private worker is provisioned. Deploy backend/Dockerfile.worker separately,
configure SCANNER_WORKER_URL and matching 32+ character SCANNER_WORKER_KEY on the
API/worker; enforce private ingress, TLS across untrusted networks, offline worker
egress and the Compose-equivalent resource/filesystem restrictions. Merely setting
a remote URL is not proof of worker isolation. Never expose this gateway publicly.

Back up the database then run `alembic upgrade head`. New tables are
email_verifications, family_groups, family_members, family_invitations,
family_alerts and user_preferences. Existing users start unverified; they can
request verification from the interface. No existing scan ownership is changed.
Use a single API instance until rate limits are backed by a shared service. Add
monitoring, retention, backup/restore tests and a professional security review.

## Verification scope

Automated coverage includes verification expiry/single use/cooldown/missing SMTP,
family consent, recipient binding, private-scan isolation, membership revocation,
preferences, optional verification gate, production worker fail-closed behavior,
authenticated real QR child-process processing and invalid ZIP handling. UI tests
include Hindi/Marathi rendering, dynamic greetings and unchanged evidence/enums.
SQLite migration round-trip, typecheck and production frontend build are checked.
Live SMTP, provider credentials, speech inference, Docker network/resource behavior
and PostgreSQL deployment must be tested by the operator; unit tests are not a
production certification. The frontend build currently reports a large-bundle
warning; this is a performance follow-up, not a successful load-test claim.
