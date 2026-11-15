# Easy deployment: one website URL

The repository now includes a **root Dockerfile** that builds the React frontend
and serves its static production files from FastAPI. Browser API requests use
`/api` on the same origin. There is no browser-facing localhost backend URL and
no Vite development server in this production image.

## Option A — local computer or VPS (recommended full stack)

Install Git, Python 3.11+ and Docker with **Compose v2.24+**. On a fresh checkout:

```sh
git clone https://github.com/Rampurkar91/SCAMSHIELD-AI.git
cd SCAMSHIELD-AI
python backend/scripts/deploy.py
```

Use the branch containing this change until its PR is merged. The launcher checks
Docker, generates missing secrets in an ignored root `.env`, validates Compose,
builds images and starts the app, PostgreSQL and the separate scanner worker.
Open **http://localhost:8080**. Initial image builds can take several minutes.
There are no default accounts: register your own.

Manual equivalent:

```sh
python backend/scripts/configure_local.py
docker compose -f compose.production.yml config --quiet
docker compose -f compose.production.yml up -d --build
```

Production startup runs Alembic migrations before accepting requests. PostgreSQL
uses a persistent named volume; worker and database ports are not exposed. The
worker inherits the existing offline network/resource/filesystem restrictions.
Only the application port is published. Do not use `down -v` unless you intend to
delete the database and model volumes. Back up data before upgrading.

### Speech model (optional operator download)

```sh
python backend/scripts/deploy.py --speech-model
```

This opts in to downloading model weights through the separate setup container.
Runtime scans never download a model. Tesseract English/Hindi/Marathi packs are
installed by the worker image. Without a speech model, voice transcription reports
unavailable; core text scans do not require any provider credentials.

### Public domain and HTTPS

Before public use, add `FRONTEND_URL=https://your-domain.example` to root `.env`.
If changing the local host port also set `APP_PORT=YOUR_PORT`. Put the app behind
an HTTPS reverse proxy, firewall direct access appropriately and restart Compose.
Use the exact HTTPS origin with no path for verification links and CORS. HTTPS is
also required by browser camera permissions outside localhost. The supplied stack
does **not** register domains, issue TLS certificates or configure a VPS firewall.

### Optional email and AI/reputation services

Create `backend/.env` from its example and fill only real owner-supplied settings:
SMTP_HOST, SMTP_PORT, SMTP_FROM_EMAIL, SMTP_USERNAME, SMTP_PASSWORD and eligible
provider keys. Compose loads this file server-side; generated deployment secrets
and service URLs override placeholder values. Never put secrets in `VITE_*`.
Missing credentials are reported explicitly, not replaced by synthetic results.
The optional verification gate is `REQUIRE_EMAIL_VERIFICATION=true`.

### Operations

```sh
docker compose -f compose.production.yml ps
docker compose -f compose.production.yml logs --tail=100 app
docker compose -f compose.production.yml logs --tail=100 scanner
# Stop without deleting stored data:
docker compose -f compose.production.yml down
# Rebuild/restart after reviewing an update and backing up data:
docker compose -f compose.production.yml up -d --build
```

Check `/health` for the database probe. The root image has a health check; a running
container alone is not proof of readiness. Once authorized as an administrator,
use runtime diagnostics to check worker/tool configuration. Do not send real
secrets or sensitive evidence while testing. Use one application instance until
shared rate limiting is implemented. Configure log redaction at the HTTPS proxy;
verification/reset URLs can contain sensitive single-use tokens.

## Option B — Render, single web service + PostgreSQL

1. Merge this change or select its branch when deploying.
2. In Render, create a Blueprint from the repository's `render.yaml`.
3. Set `FRONTEND_URL` to your exact public Render/custom-domain origin.
4. The Blueprint uses the root Dockerfile: **one URL hosts the UI and API**.
   PostgreSQL and a generated JWT key are configured by the Blueprint. Hosting
   may incur charges; review provider pricing before creating resources.
5. Add optional credentials in server environment settings, never in source code.

**Binary file scanning stays disabled on this API-only Blueprint** until an
isolated private worker is provisioned and SCANNER_WORKER_URL / SCANNER_WORKER_KEY
are configured. Follow FAMILY_I18N_WORKER_SETUP.md for those security requirements.
A worker on an unrestricted network is not equivalent to the Compose isolation.
Render alone does not automatically provision the offline scanner or model volume.

## What is / is not verified

Automated tests cover static assets, client-route refreshes, missing builds,
private/dot-file rejection, API routing and missing-asset behavior. Existing
backend/frontend tests and the frontend production build should be run for every
change. The added deployment workflow validates Compose configuration and builds
and smoke-tests the container in GitHub Actions; inspect its actual result rather
than assuming a pass. Docker/PostgreSQL/cloud/TLS/model/SMTP/live-provider operation
has not been verified in the editing sandbox. Setup code is not proof of a live
public deployment. Existing unversioned development databases need a schema audit,
not a blind Alembic stamp or destructive reset.
