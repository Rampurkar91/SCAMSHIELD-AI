# System architecture and workflows

```mermaid
flowchart LR
 Browser[React / Vite / Tailwind / TypeScript + existing JSX] -->|JWT bearer + bounded JSON or file| API[FastAPI authenticated routes]
 API --> Auth[Argon2 + version-revoked JWT]
 API --> Local[Local rules + transparent risk engine]
 API --> Files[Bounded in-memory image / QR / email / ZIP inspection]
 Files --> OCR[Optional local Tesseract]
 Files --> Voice[Optional local faster-whisper]
 API --> ML[Trusted offline-trained English SMS model]
 API -->|Explicit disclosure opt-in| Providers[Fixed-endpoint reputation / Gemini / OSV]
 API --> ORM[SQLAlchemy sessions]
 ORM --> DB[(PostgreSQL production / SQLite preview)]
 API --> Reports[ReportLab PDF / CSV]
 API --> SMTP[Configured STARTTLS reset email]
 Training[Download provenance + offline scikit-learn training] --> ML
 Alembic[Alembic migrations] --> DB
```

```mermaid
flowchart TD
 Input[User submission] --> Validation[Authenticate + body/type/size validation]
 Validation --> Parse[Parse text, image, QR, email, WAV or source ZIP]
 Parse --> Rules[Deduplicate local evidence]
 Rules --> Advisory[Optional ML label / opt-in AI explanation]
 Rules --> Intel[Opt-in fixed-provider reputation lookup]
 Intel --> Score[Local score, minimum 90 for provider threat match]
 Advisory --> Save[Persist owned result with source labels and limits]
 Score --> Save
 Save --> Critical{Score at least 80?}
 Critical -->|Yes| Notice[Persist private critical notification]
 Critical --> History[Private history / dashboard / export / delete]
 Notice --> History
```

## Data and trust boundaries
`users` owns `scans`, `reports`, `reset_tokens`, `notifications`, and `quiz_attempts` via indexed foreign keys. Scan results and indicators are stored as JSON. `security_api_logs` stores only provider/status/timestamp; it does not store keys, messages or submitted URLs. A second migration adds notifications, quiz attempts and provider logs.

JWTs are stored in sessionStorage, expire by default after 30 minutes, and are invalidated across sessions by logout/password changes. This avoids ambient-cookie CSRF but JavaScript-accessible tokens remain vulnerable to XSS; evaluate a hardened cookie/session design before production. React renders untrusted output as text, not HTML.

No submitted website is fetched. Reputation lookup endpoints are fixed. GitHub retrieval accepts only a strict github.com owner/repo URL, queries fixed API endpoints, pins an immutable commit and bounds the codeload archive. No git command, repository hook or source code is executed.

Uploads are body-bounded before multipart parsing, then validated by their processing pipeline. Images have MIME/content/pixel checks. ZIPs are inspected in memory without extraction, reject traversal/symlinks/encryption and enforce expansion/file-count caps. Code findings omit matched lines to avoid disclosing secrets. Original uploads are discarded; text and findings remain until scan deletion. Optional Whisper uses a temporary WAV deleted after processing.

OCR/voice processing currently uses bounded inputs and a thread, not a separate OS sandbox/queue. Deploy dedicated resource-limited workers before accepting unrestricted public workloads. The application does not run external Semgrep/Bandit/Gitleaks tools or arbitrary user code.

External checks require per-request consent; external services' retention/terms still apply. Rule-based risk, provider evidence, ML spam labels and AI explanations are displayed separately. Only real provider matches establish the 90-point score floor; neither AI prose nor ML labels are treated as independently verified fraud evidence.
