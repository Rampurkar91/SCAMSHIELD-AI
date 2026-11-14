# API and dataset setup guide

All private credentials belong in **backend/.env**, not frontend source or VITE variables. Copy `backend/.env.example`, configure the variables you actually need, then restart the API. The backend loads this file with python-dotenv without overriding exported variables. Do not commit `.env`.

External URL disclosure and Gemini analysis are **off by default on every scan**. UI checkboxes or `use_external: true` / `use_ai: true` explicitly authorize disclosure to configured providers. Do not send private URLs, tokens or confidential messages to external providers. Provider results, local rules, ML labels and AI explanations remain separate. Every result states what did not run.

| Service / dataset | Purpose | Registration / download | Environment variable |
|---|---|---|---|
| Gemini | Structured contextual explanation and security assistant | [Google AI Studio](https://aistudio.google.com/apikey); [SDK docs](https://ai.google.dev/gemini-api/docs/get-started) | `GEMINI_API_KEY`, optional `GEMINI_MODEL` |
| Google Safe Browsing | Unsafe URL reputation lookup | [Google Cloud](https://console.cloud.google.com/); enable Safe Browsing API; [docs](https://developers.google.com/safe-browsing/reference/rest) | `GOOGLE_SAFE_BROWSING_API_KEY` |
| PhishTank | Verified phishing URL lookup | [Developer information](https://www.phishtank.org/developer_info.php); register and request an app key | `PHISHTANK_API_KEY` |
| URLhaus | Malware-distribution URL lookup, not general phishing | [abuse.ch API](https://urlhaus.abuse.ch/api/); obtain an Auth-Key | `URLHAUS_AUTH_KEY` |
| VirusTotal | Optional existing URL-report lookup | [VirusTotal](https://www.virustotal.com/); account API-key settings; [docs](https://docs.virustotal.com/docs/api-overview) | `VIRUSTOTAL_API_KEY` |
| UCI SMS Spam | English SMS spam baseline | [UCI official dataset](https://archive.ics.uci.edu/dataset/228/sms+spam+collection); script uses a documented GitHub mirror | None |
| UCI Spambase | Numeric email spam research baseline | [UCI official dataset](https://archive.ics.uci.edu/dataset/94/spambase); script uses documented GitHub mirror | None |
| Tesseract | Local screenshot OCR | [Tesseract](https://github.com/tesseract-ocr/tesseract); install package and language data | Optional `TESSERACT_CMD`, `OCR_LANG` |
| OSV | Known dependency vulnerabilities | [Public API](https://google.github.io/osv.dev/api/), no registration normally required | No API key |
| faster-whisper | Optional local WAV transcription | Install optional requirements and download a model during operator setup | `WHISPER_MODEL_PATH` |
| SMTP | Password-reset email | Your mail provider's SMTP settings; use an authorized sender and SMTP/app password | `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_EMAIL`, `SMTP_USERNAME`, `SMTP_PASSWORD` |

## Credential setup and live checks
1. Register using the links above, review terms, enable the relevant API, and obtain a server-side key. Some providers may restrict account creation or require an eligible application; a key is not guaranteed.
2. Put each key in the matching variable in `backend/.env`. Never paste private credentials into chat or frontend code. Restrict cloud keys to the appropriate API and server environment.
3. Start the API and register/login. `GET /health` shows configured vs missing services, not proof of reachability. Administrators can use `/admin` and `GET /api/admin/integrations/status` for actual most-recent outcomes and last-success timestamps. Configuration status never returns keys.
4. Scan `https://example.com` with **Send extracted URLs to configured reputation providers** enabled. It is a harmless lookup input, not a test of guaranteed safety. Inspect each provider status. No submitted destination is visited by ScamShield.
5. For Gemini, enable the scan AI checkbox or use the assistant with **Send my question to Gemini**. Ask “Explain why a UPI PIN is not needed to receive money.” An `ok` result is labeled as an AI explanation, not independent verification.
6. For OSV, upload a safe source ZIP containing a pinned `requirements.txt` or `package-lock.json`, then explicitly enable dependency disclosure. At most 10 exact package versions are checked. Errors are shown per lookup. No code is sent to OSV.
7. For SMTP, request a password reset for an account you own and confirm the actual mailbox receives the link. Tokens are single-use, hashed in the database and expire after 20 minutes. Live delivery is not verified in the sandbox.

### Missing keys and failures
- Missing reputation key: `not_configured`, **not** `no_match`.
- HTTP 429: `rate_limited`; failed or malformed response: `error`.
- VirusTotal 404: `not_found`. We do not submit new URLs or files to VirusTotal.
- A provider match establishes a 90-point minimum risk; separate local rule contributions are retained. AI and ML do not independently increase the score.
- Missing/failed Gemini: assistant returns clearly labeled static safety guidance in the selected language. It never pretends the fallback is AI-generated.
- Missing local model: rule-based scans still run, with `ml.status=unavailable`.
- Missing OCR/Whisper software: explicit 503, not a fabricated transcript.
- Outbound host restrictions in this Arena sandbox prevent live AI/reputation/OSV verification even when adapters are present. Tests use labeled mocks. Never disable TLS verification to work around networking problems.

### Terms, quotas and operational limits
- Safe Browsing's non-commercial eligibility must be checked for this project. A commercial deployment should evaluate Web Risk; a Web Risk adapter is not implemented.
- PhishTank requires a descriptive User-Agent and appropriate key/quota usage; the adapter uses per-URL lookup, not bulk feeds.
- URLhaus is malware intelligence, not a universal scam database. Respect Auth-Key and usage policy.
- VirusTotal public-API limits and non-commercial restrictions apply. Do not enable it for a commercial product without suitable authorization.
- Gemini content may be processed/retained under your account's policies. Rate limits and billing are provider-specific.
- Calls have finite timeouts and no quota-bypassing retries. Full distributed provider quota budgeting is not implemented. Keep deployments single-instance until shared controls are installed.

## Install OCR and test
Ubuntu/Debian (outside the restricted sandbox):
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar
export OCR_LANG=eng+hin+mar
# Optional if not on PATH:
export TESSERACT_CMD=/usr/bin/tesseract
tesseract --version
```
Upload a PNG with clearly printed synthetic text to `/image`. The Docker backend installs these packages. It does not perform image-tampering forensics or independently verify payment success. QR scanning uses OpenCV locally and does not require Tesseract. Camera capture is not implemented.

## Optional local speech setup
```bash
.venv/bin/pip install -r backend/requirements-voice.txt
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base', local_dir='backend/models/whisper-base')"
# In backend/.env use an absolute path:
# WHISPER_MODEL_PATH=/absolute/path/to/repo/backend/models/whisper-base
```
Model download needs access to the model host, not available in this sandbox. The request handler only loads local files and never downloads a model on a user request. Current audio support is PCM WAV, 1–120 seconds, at most 8 MiB. Consent is required. No dedicated voice-synthesis/deepfake model is integrated. Production transcription needs a separately resource-limited worker; the present optional path runs in a thread with fixed model CPU threads and is not ready for unrestricted public workload.

## Datasets, training and reproducibility
```bash
.venv/bin/python -m backend.scripts.download_datasets all
.venv/bin/python -m backend.scripts.train_models sms
.venv/bin/python -m backend.scripts.train_models email
# Only if you have a legally usable labeled URL CSV:
.venv/bin/python -m backend.scripts.train_models url --input /path/to/licensed-urls.csv
```
If your development network uses a locally trusted enterprise CA, set `SSL_CERT_FILE` to its CA bundle (in this sandbox `/etc/ssl/certs/ca-certificates.crt` was used). Never use `verify=False`.

Raw datasets and `.joblib` artifacts are ignored by Git. Download hashes, GitHub blob versions, dates, license references and real held-out metrics live in `backend/datasets/metadata/`. Re-run training on a fresh checkout to install the SMS model. Do not load an untrusted Joblib artifact: it can execute code. [Dataset documentation](datasets.md) explains class/usage limits.
