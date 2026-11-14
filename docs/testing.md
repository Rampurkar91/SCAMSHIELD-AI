# Testing and safe demonstration

```bash
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
cd frontend
npx playwright install --with-deps chromium
# With both servers running:
npx playwright test
npm audit
cd ..
.venv/bin/pip install pip-audit
.venv/bin/pip-audit -r backend/requirements.txt
```

Backend tests use a temporary SQLite database, never the real preview history. Provider and OCR mocks are explicit: passing mocked tests does not mean a real service was contacted. Actual QR decoding uses a generated harmless UPI payload. ZIP fixtures include safe, intentionally vulnerable text; none is executed. Voice tests validate consent, WAV constraints, missing model behavior and a mocked local transcript. One trusted-SMS-artifact test skips on fresh checkouts until the documented training command has produced a model.

Coverage includes authentication/revocation, reset, ownership, risk evidence, mixed awareness/malicious sentence regression, URL syntax, UPI action interpretation, file size/content checks, QR, image OCR fallbacks, ZIP path traversal, secret redaction, email parsing, notifications, quiz ownership, admin role checks, provider errors/quotas, Gemini JSON validation and ML fallback.

UI tests cover account validation, API errors, upload limits, voice consent, missing OCR, assistant fallback labeling, quiz submission and denied admin access. Latest local run: **36 backend tests**, **16 frontend tests**, TypeScript check and production build pass. Both dependency audits report no known vulnerabilities. **Three Playwright scenarios passed in separate sandbox Chromium invocations** (single-process Chromium is unstable when reusing contexts here).

Playwright covers real QR/static-ZIP uploads, explicitly labeled assistant fallback and saved quiz reload, plus account -> URL scan -> persisted history -> PDF/CSV -> logout/login, plus mobile overflow/navigation. Further manual verification is required for all browsers, full accessibility and every advanced module.

## Safe demo (about 3 minutes)
1. Register and show a genuinely empty dashboard.
2. Scan `https://example.com`; explain that low risk is not guaranteed safety.
3. Use synthetic `http://paypal-verify.xyz/login` as text input only; never navigate to it.
4. Analyze “To receive your refund, enter your UPI PIN and approve the collect request.”
5. Show the actual English SMS spam baseline label separately from rule risk and provider coverage.
6. Upload a controlled QR image, or a screenshot of synthetic text if Tesseract is installed. Show extracted payload/text; do not initiate a payment.
7. Open assistant: show real Gemini only if a configured call succeeds; otherwise explicitly show static fallback.
8. Open private history, download a PDF, then show 1930/emergency guidance.

Developer demo: ZIP a tiny `app.py` containing `eval(user_input)` and an obviously synthetic `api_key="EXAMPLE-NOT-A-REAL-SECRET"`. Show findings and remediation, noting that built-in rules are used, not external static-analysis tools. Secret values are omitted from results.

No test fixture or synthetic scenario is presented as independently verified threat intelligence. Metrics are tied to recorded dataset hashes and are not a calibrated fraud probability.

## CI
`.github/workflows/test.yml` runs unit/UI/type/build checks and provisions a disposable PostgreSQL 16 service for Alembic plus an opt-in real-database smoke journey. This CI job has been added, not yet observed running successfully on GitHub. The database smoke script requires `ALLOW_DATABASE_SMOKE_TEST=true`; run it only on an isolated test database, never on customer data. GitHub CI results, not local SQLite tests, determine whether PostgreSQL has actually passed.
