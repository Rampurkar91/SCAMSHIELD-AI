import React, {
  useState,
  useEffect,
  type ComponentType,
  type FormEvent,
} from "react";
import { Link } from "react-router-dom";
import {CameraCapture} from "./CameraCapture";
import{RuntimeSetup}from"./RuntimeSetup";
import{useLocale}from"../i18n/core";
import {
  Camera,
  QrCode,
  Code2,
  AudioLines,
  Mail,
  Upload,
  LoaderCircle,
  ShieldCheck,
  Info,
  MessageSquare,
  Send,
  Check,
  Bell,
} from "lucide-react";
import { api, errorText } from "../api";
import type {
  ScanRecord,
  IntegrationStatus,
  ThreatReport,
} from "../types/security";

type UploadKind = "image" | "qr" | "code" | "voice" | "email-file";
const uploads: Record<
  UploadKind,
  {
    title: string;
    accept: string;
    mime: string[];
    max: number;
    description: string;
  }
> = {
  image: {
    title: "Screenshot scanner",
    accept: ".jpg,.jpeg,.png,.webp",
    mime: ["image/jpeg", "image/png", "image/webp"],
    max: 5,
    description:
      "Extract screenshot text with local Tesseract OCR, decode QR codes and analyze suspicious instructions. Images are discarded after processing; extracted content is saved privately.",
  },
  qr: {
    title: "QR safety check",
    accept: ".jpg,.jpeg,.png,.webp",
    mime: ["image/jpeg", "image/png", "image/webp"],
    max: 5,
    description:
      "Decode a QR image without opening its destination. Inspect a URL or UPI payment intent before taking action.",
  },
  code: {
    title: "Developer security",
    accept: ".zip",
    mime: [],
    max: 5,
    description:
      "Static source-ZIP review for secrets and unsafe patterns. No source code is executed. Limits: 300 entries, 10 MiB expanded, 512 KiB per file. Findings are saved; original ZIPs are discarded.",
  },
  voice: {
    title: "Voice scam analyzer",
    accept: ".wav",
    mime: ["audio/wav", "audio/x-wav", "audio/wave"],
    max: 8,
    description:
      "Analyze a transcript of a recording you are authorized to share. Requires an installed local Whisper model. PCM WAV only, 1–120 seconds. Transcript analysis cannot prove voice authenticity.",
  },
  "email-file": {
    title: "Email file scanner",
    accept: ".eml",
    mime: [],
    max: 0.5,
    description:
      "Read the plain-text part of an .eml message and inspect supplied headers. Attachments are listed, never executed. HTML-only email is not accepted.",
  },
};
function Failure({ message }: { message: string }) {
  return message ? (
    <div className="error-box" role="alert">
      <Info size={17} />
      {message}
    </div>
  ) : null;
}
export function UploadScanner({
  kind,
  Result,
}: {
  kind: UploadKind;
  Result: ComponentType<{ scan: ScanRecord }>;
}) {
  const info = uploads[kind],
    [file, setFile] = useState<File | null>(null),
    [consent, setConsent] = useState(false),
    [osv, setOsv] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<ScanRecord | null>(null);
  useEffect(() => {
    setFile(null);
    setResult(null);
    setError("");
    setConsent(false);
  }, [kind]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!file) {
      setError("Choose a file first.");
      return;
    }
    if (file.size > info.max * 1024 * 1024) {
      setError(`File exceeds ${info.max} MiB.`);
      return;
    }
    if (info.mime.length && !info.mime.includes(file.type)) {
      setError("Unsupported file format.");
      return;
    }
    if (kind === "voice" && !consent) {
      setError("Explicit audio processing consent is required.");
      return;
    }
    setBusy(true);
    setResult(null);
    const body = new FormData();
    body.append("file", file);
    body.append("mode", kind);
    body.append("consent", String(consent));
    body.append("check_dependencies", String(osv));
    try {
      const response = await api.post("/scans/" + kind, body, {
        timeout: 180000,
      });
      setResult(response.data);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">PAUSE. INSPECT. PROTECT.</div>
          <h1>{info.title}</h1>
          <p>Private analysis with clear evidence and explicit limitations.</p>
        </div>
      </div>
      <section className="panel padded upload-panel">
        <span className="large-scan-icon">
          {kind === "qr" ? (
            <QrCode />
          ) : kind === "code" ? (
            <Code2 />
          ) : kind === "voice" ? (
            <AudioLines />
          ) : kind === "email-file" ? (
            <Mail />
          ) : (
            <Camera />
          )}
        </span>
        <h2>{info.title}</h2>
        <p>{info.description}</p>
        {kind === "qr" && <CameraCapture disabled={busy} onCapture={captured=>{setFile(captured);setResult(null);setError("")}}/>}
        <form onSubmit={submit}>
          <label htmlFor={"upload-" + kind}>
            Choose file · maximum {info.max} MiB
          </label>
          <div className="upload-drop">
            <Upload size={25} />
            <input
              key={kind}
              id={"upload-" + kind}
              type="file"
              accept={info.accept}
              required={!file}
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setResult(null);
              }}
            />
            <span>
              {file ? file.name : "Your original file is not retained."}
            </span>
          </div>
          {kind === "voice" && (
            <label className="consent">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              I have permission to upload this recording and consent to local
              transcription.
            </label>
          )}
          {kind === "code" && (
            <label className="consent">
              <input
                type="checkbox"
                checked={osv}
                onChange={(e) => setOsv(e.target.checked)}
              />
              Send up to 10 exact dependency names and versions to OSV for
              vulnerability checks. Source files are not sent.
            </label>
          )}
          <Failure message={error} />
          <button className="btn primary" disabled={busy}>
            {busy ? (
              <LoaderCircle size={17} className="spin" />
            ) : (
              <ShieldCheck size={17} />
            )}{" "}
            {busy ? "Processing…" : "Analyze file"}
          </button>
        </form>
        <div className="notice upload-notice">
          <Info size={17} />
          <p>
            Do not upload secrets or private conversations without
            authorization. Screenshots cannot verify a payment. Local
            OCR/transcription may be unavailable if required software is not
            installed.
          </p>
        </div>
      </section>
      {result && <Result scan={result} />}
    </>
  );
}
export function Assistant() {
  const locale=useLocale();
  useEffect(()=>setLanguage({en:"English",hi:"Hindi",mr:"Marathi"}[locale]),[locale]);
  const [message, setMessage] = useState(""),
    [language, setLanguage] = useState("English"),
    [useAI, setAI] = useState(false),
    [context, setContext] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [messages, setMessages] = useState<
      Array<{ role: string; text: string; source?: string; status?: string }>
    >([]);
  async function send(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const previous = messages;
    setMessages([...previous, { role: "You", text: message }]);
    const submitted = message;
    setMessage("");
    try {
      const r = await api.post(
        "/assistant/chat",
        {
          message: submitted,
          language,
          use_ai: useAI,
          context: context
            ? previous
                .slice(-6)
                .map((m) => (m.role + ": " + m.text).slice(0, 1000))
            : [],
        },
        { timeout: 25000 },
      );
      setMessages((m) => [
        ...m,
        {
          role: "ScamShield",
          text:
            r.data.explanation +
            "\n\n" +
            r.data.actions.join("\n") +
            "\n\n" +
            r.data.uncertainty,
          source: r.data.source,
          status: r.data.status,
        },
      ]);
    } catch (e) {
      setError(errorText(e));
      setMessage(submitted);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">ASK. UNDERSTAND. STAY SAFER.</div>
          <h1>Cybersecurity assistant</h1>
          <p>
            Contextual AI when configured. Clearly identified general guidance
            otherwise.
          </p>
        </div>
      </div>
      <section className="panel padded">
        <div className="assistant-settings">
          <label>
            Response language
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option>English</option>
              <option>Hindi</option>
              <option>Marathi</option>
            </select>
          </label>
          <label className="consent">
            <input
              type="checkbox"
              checked={useAI}
              onChange={(e) => setAI(e.target.checked)}
            />
            Send my question to Gemini for AI analysis
          </label>
          <label className="consent">
            <input
              type="checkbox"
              checked={context}
              onChange={(e) => setContext(e.target.checked)}
            />
            Include recent conversation context
          </label>
        </div>
        <p>
          No chat history is saved to the database. If enabled, your
          question/context is sent to Google under its policies. Never enter a
          password, OTP or PIN.
        </p>
        <div className="chat-log">
          {!messages.length && (
            <div className="empty-state">
              <MessageSquare size={30} />
              <h3>Not sure about a payment request?</h3>
              <p>
                Ask how to recognize a UPI collect scam or what to do after
                clicking a suspicious link.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={
                "chat-message " + (m.role === "You" ? "user-message" : "")
              }
            >
              <strong>{m.role}</strong>
              {m.source && (
                <small>
                  {m.source} · {m.status}
                </small>
              )}
              <p translate="no">{m.text}</p>
            </div>
          ))}
        </div>
        <Failure message={error} />
        <form onSubmit={send}>
          <label htmlFor="question">Your question</label>
          <textarea
            id="question"
            rows={3}
            required
            minLength={3}
            maxLength={4000}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="What should I do if someone asks for a PIN to send a refund?"
          />
          <div className="form-actions">
            <button
              type="button"
              className="btn secondary"
              onClick={() => setMessages([])}
            >
              Clear conversation
            </button>
            <button className="btn primary" disabled={busy}>
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <Send size={16} />
              )}{" "}
              {busy ? "Responding…" : "Ask ScamShield"}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
export function Learning() {
  const [data, setData] = useState<{
      quizzes: Array<{ id: string; question: string; options: string[] }>;
      attempts: Array<{ id: number; score: number; quiz_id: string }>;
    }>({ quizzes: [], attempts: [] }),
    [error, setError] = useState(""),
    [feedback, setFeedback] = useState<Record<string, string>>({});
  const load = () =>
    api
      .get("/awareness/quizzes")
      .then((r) => setData(r.data))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, []);
  async function answer(id: string, index: number) {
    try {
      const r = await api.post("/awareness/quizzes/" + id + "/submit", {
        answer: index,
      });
      setFeedback((f) => ({
        ...f,
        [id]: r.data.score + "/100 · " + r.data.explanation,
      }));
      load();
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">LEARN ONE SAFER HABIT</div>
          <h1>Safety quizzes</h1>
          <p>Practice, review explanations and track your saved attempts.</p>
        </div>
      </div>
      <Failure message={error} />
      {data.quizzes.map((q) => (
        <section className="panel padded quiz" key={q.id}>
          <h2>{q.question}</h2>
          {q.options.map((o, i) => (
            <button
              key={o}
              className="quiz-option"
              onClick={() => answer(q.id, i)}
            >
              {o}
            </button>
          ))}
          {feedback[q.id] && <p className="success-text">{feedback[q.id]}</p>}
        </section>
      ))}
      <section className="panel padded">
        <h2>Your recent attempts</h2>
        {data.attempts.length ? (
          data.attempts.map((a) => (
            <p key={a.id}>
              {a.quiz_id} · {a.score}/100
            </p>
          ))
        ) : (
          <p>No attempts yet.</p>
        )}
      </section>
    </>
  );
}
export function Notifications() {
  const [items, setItems] = useState<
      Array<{ id: number; message: string; read: boolean }>
    >([]),
    [error, setError] = useState("");
  const load = () =>
    api
      .get("/notifications")
      .then((r) => setItems(r.data))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, []);
  async function read(id: number) {
    try {
      await api.put("/notifications/" + id + "/read");
      load();
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">YOUR SAVED SECURITY EVENTS</div>
          <h1>Notifications</h1>
          <p>Critical scan alerts from your own activity.</p>
        </div>
      </div>
      <Failure message={error} />
      <section className="panel padded">
        {items.length ? (
          items.map((n) => (
            <div className="report-item" key={n.id}>
              <Bell size={19} />
              <p>{n.message}</p>
              {!n.read ? (
                <button className="btn secondary" onClick={() => read(n.id)}>
                  Mark as read
                </button>
              ) : (
                <small className="muted">Read</small>
              )}
            </div>
          ))
        ) : (
          <div className="empty-state">
            <Bell size={25} />
            <h3>You're all caught up.</h3>
            <p>Critical scan results will appear here.</p>
          </div>
        )}
      </section>
    </>
  );
}
export function Admin() {
  const [providers, setProviders] = useState<IntegrationStatus[]>([]),
    [reports, setReports] = useState<ThreatReport[]>([]),
    [stats, setStats] = useState<Record<string, number>>({}),
    [error, setError] = useState("");
  const load = () =>
    Promise.all([
      api.get("/admin/integrations/status"),
      api.get("/admin/reports"),
      api.get("/admin/dashboard"),
    ])
      .then(([p, r, s]) => {
        setProviders(p.data);
        setReports(r.data);
        setStats(s.data);
      })
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, []);
  async function status(id: number, status: string) {
    try {
      await api.put("/admin/reports/" + id, { status });
      load();
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">AUTHORIZED ADMINISTRATORS ONLY</div>
          <h1>Administration</h1>
          <p>
            Actual provider configuration and report review. No secrets are
            displayed.
          </p>
        </div>
        <button className="btn secondary" onClick={load}>
          Refresh
        </button>
      </div>
      <Failure message={error} />
      <div className="stat-grid">
        {Object.entries(stats).map(([k, v]) => (
          <div className="stat-card" key={k}>
            <span className="capitalize">{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
      <section className="panel padded">
        <h2>Integration status</h2>
          {providers.length>0&&<RuntimeSetup/>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>PROVIDER</th>
                <th>CONFIGURATION</th>
                <th>LAST RESULT</th>
                <th>LAST SUCCESS</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td>{p.configured ? "Configured" : "Not configured"}</td>
                  <td>{p.availability}</td>
                  <td>{p.last_success || "Never checked successfully"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          Configuration does not prove reachability. Status is based on actual
          requests, not automatic probes.
        </p>
      </section>
      <section className="panel padded">
        <h2>Threat review queue</h2>
        {reports.length ? (
          reports.map((r) => (
            <div className="report-item" key={r.id}>
              <h3>
                #{r.id} · {r.category}
              </h3>
              <p>{r.description}</p>
              <label>
                Review status
                <select
                  value={r.status}
                  onChange={(e) => status(r.id, e.target.value)}
                >
                  {[
                    "Submitted",
                    "Under Review",
                    "Confirmed Threat",
                    "Not Verified",
                    "Resolved",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
          ))
        ) : (
          <p>No reports to review.</p>
        )}
      </section>
    </>
  );
}
export function Shopkeeper() {
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">SIMPLE CHECKS FOR YOUR SHOP</div>
          <h1>Before you hand over the goods.</h1>
          <p>
            Check payments in your own bank app. Never rely on someone else's
            screenshot.
          </p>
        </div>
      </div>
      <div className="quick-grid shopkeeper-grid">
        {[
          ["/scan?type=upi", "Check a payment message", MessageSquare],
          ["/image", "Inspect a screenshot", Camera],
          ["/qr", "Read a QR code safely", QrCode],
          ["/emergency", "Get fraud help now", ShieldCheck],
        ].map(([url, title, I]) => {
          const Icon = I as typeof Camera;
          return (
            <Link className="quick-card" to={url as string} key={url as string}>
              <Icon size={33} />
              <h2>{title as string}</h2>
              <p>Open safety check →</p>
            </Link>
          );
        })}
      </div>
      <section className="panel padded">
        <h2>Money received? Verify it yourself.</h2>
        <p>
          A UPI PIN authorizes a payment from your account. A screenshot, SMS or
          sound from another person's phone cannot independently prove a payment
          succeeded.
        </p>
      </section>
    </>
  );
}
