import React, { useState, type FormEvent, type ComponentType } from "react";
import { Github, LoaderCircle } from "lucide-react";
import { api, errorText } from "../api";
import type { ScanRecord } from "../types/security";
export function GitHubScanner({
  Result,
}: {
  Result: ComponentType<{ scan: ScanRecord }>;
}) {
  const [url, setURL] = useState(""),
    [authorized, setAuthorized] = useState(false),
    [dependencies, setDependencies] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<ScanRecord | null>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const r = await api.post(
        "/scans/github",
        { url, authorized, check_dependencies: dependencies },
        { timeout: 180000 },
      );
      setResult(r.data);
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
          <div className="eyebrow">READ-ONLY PUBLIC SOURCE REVIEW</div>
          <h1>GitHub repository scan</h1>
          <p>
            Inspect a bounded, commit-pinned public source archive. No code is
            executed.
          </p>
        </div>
      </div>
      <section className="panel padded">
        <Github size={35} />
        <form onSubmit={submit}>
          <label htmlFor="repo">Public repository URL</label>
          <input
            id="repo"
            type="url"
            required
            maxLength={300}
            value={url}
            onChange={(e) => setURL(e.target.value)}
            placeholder="https://github.com/owner/repository"
          />
          <label className="consent">
            <input
              type="checkbox"
              checked={authorized}
              onChange={(e) => setAuthorized(e.target.checked)}
              required
            />
            I am authorized to review this public repository.
          </label>
          <label className="consent">
            <input
              type="checkbox"
              checked={dependencies}
              onChange={(e) => setDependencies(e.target.checked)}
            />
            Send up to 10 exact dependency names and versions to OSV.
          </label>
          <p>
            Limits: 5 MiB archive, 10 MiB expanded, 300 entries, 512 KiB per
            file. Private repositories are not supported; no GitHub token is
            requested. Findings use built-in static rules, not a full security
            audit.
          </p>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
          <button className="btn primary" disabled={busy}>
            {busy ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <Github size={16} />
            )}{" "}
            {busy ? "Inspecting…" : "Scan repository"}
          </button>
        </form>
      </section>
      {result && <Result scan={result} />}
    </>
  );
}
