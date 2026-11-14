# Deployment

No cloud or Docker deployment has been verified in this sandbox. PostgreSQL SQLAlchemy configuration and migrations are included, but runtime PostgreSQL connectivity must be tested in your environment.

## Docker Compose local stack
Install Docker/Compose, create a repository-root `.env` (ignored) containing a strong `POSTGRES_PASSWORD` and random `JWT_SECRET_KEY`. Use a URL-safe database password or URL-encode it when configuring the database URL.

```bash
# Generate values locally; never commit them:
python -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build
```
Frontend: http://localhost:5173. API: http://localhost:8000/docs. Database is not exposed on a host port. Frontend browser calls `/api`; Vite proxies inside the container network to `api:8000`. The backend Dockerfile installs Tesseract and English/Hindi/Marathi language data. Model artifacts are deliberately excluded; train/install them explicitly. The frontend container is a development server for local use, not a hardened production web server.

## Render
`render.yaml` uses a Docker backend so the Tesseract OS dependency is available. It provisions PostgreSQL and a generated JWT key; set `FRONTEND_URL` to the exact Vercel origin. Optional keys must be added in Render's secret environment settings. Docker startup runs `alembic upgrade head` then Uvicorn. Set `PORT` through Render as usual. Use one API instance until shared rate limits and scan-worker isolation are implemented.

For a non-Docker deployment, build with `pip install -r requirements.txt`; start with `alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`. Install Tesseract separately or OCR returns an explicit 503. Set `APP_ENV=production`, `DATABASE_URL`, a strong `JWT_SECRET_KEY` and `FRONTEND_URL`.

## Vercel
Root `frontend`; install `npm ci`; build `npm run build`; output `dist`. Set `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE/api` and rebuild. `vercel.json` rewrites SPA routes. No credentials belong in `VITE_*` variables. Ensure the backend allows the exact frontend origin; preview origins are not broadly enabled by default.

## Verify before public release
1. Back up the database, run migrations, and verify `/health` returns `database: connected`.
2. Register/login, save a scan, reload, export PDF/CSV, and verify another user cannot read it.
3. Verify real SMTP reset delivery and reset-token single use.
4. Enable only legally eligible providers, test consent and all failure statuses.
5. Install a trusted model artifact and verify its provenance before enabling it.
6. Verify OCR and optional speech on harmless authorized samples.
7. Add distributed limits, egress restrictions, TLS, CSP/gateway headers, monitoring, backup encryption, automated retention and isolated resource-constrained workers.
8. Perform a professional security review and a PostgreSQL-backed integration/load test. Do not interpret unit tests as production certification.
