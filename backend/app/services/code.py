"""Bounded static text inspection; never extract ZIPs or execute submitted code."""

import io, re, stat, zipfile
from pathlib import PurePosixPath
from fastapi import HTTPException
from ..engine import ACTIONS
from ..integrations.providers import osv_query

PATTERNS = [
    (
        "hardcoded_secret",
        "high",
        r"""(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"'\n]{8,}["']""",
        "Move secrets to a secret manager; rotate any exposed credentials.",
    ),
    (
        "private_key",
        "critical",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "Remove and rotate the private key; inspect repository history.",
    ),
    (
        "unsafe_eval",
        "high",
        r"\b(?:eval|exec)\s*\(",
        "Avoid executing untrusted strings; use structured parsers.",
    ),
    (
        "shell_execution",
        "high",
        r"shell\s*=\s*True",
        "Avoid shell=True; use fixed argument arrays and allowlists.",
    ),
    (
        "debug_enabled",
        "moderate",
        r"(?i)debug\s*[:=]\s*(?:true|1)",
        "Disable debug mode in deployed environments.",
    ),
    (
        "unsafe_html",
        "moderate",
        r"dangerouslySetInnerHTML|\.innerHTML\s*=",
        "Avoid rendering untrusted HTML; sanitize with a vetted library.",
    ),
    (
        "sql_string_interpolation",
        "high",
        r"""(?i)(?:execute|executemany)\s*\(\s*f["']""",
        "Use parameterized SQL; review interpolation before execution.",
    ),
]
TEXT_EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
    ".env",
    ".php",
    ".html",
    ".ini",
    ".cfg",
    ".sql",
}


def scan_zip(raw, check_dependencies=False):
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "ZIP exceeds 5 MiB.")
    findings = []
    scanned = 0
    total = 0
    dependencies = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = archive.infolist()
            if len(files) > 300:
                raise HTTPException(413, "ZIP has more than 300 entries.")
            for entry in files:
                path = PurePosixPath(entry.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.filename
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise HTTPException(
                        422, "ZIP contains unsafe paths or symbolic links."
                    )
                if entry.flag_bits & 1:
                    raise HTTPException(422, "Encrypted ZIP entries are not supported.")
                total += entry.file_size
                if total > 10 * 1024 * 1024 or entry.file_size > 512 * 1024:
                    raise HTTPException(
                        413,
                        "ZIP exceeds expanded size limits (10 MiB total, 512 KiB per entry).",
                    )
                if entry.is_dir() or (
                    path.suffix.lower() not in TEXT_EXT
                    and path.name not in {".env", "Dockerfile"}
                ):
                    continue
                data = archive.read(entry)
                if len(data) > 512 * 1024:
                    raise HTTPException(413, "Expanded file exceeds limit.")
                text = data.decode("utf-8", errors="replace")
                scanned += 1
                for number, line in enumerate(text.splitlines(), 1):
                    if len(findings) >= 200:
                        break
                    for code, severity, pattern, fix in PATTERNS:
                        if re.search(pattern, line):
                            # Do not return matched source lines: they can contain secrets.
                            findings.append(
                                {
                                    "code": code,
                                    "severity": severity,
                                    "file": str(path)[:300],
                                    "line": number,
                                    "remediation": fix,
                                }
                            )
                            if len(findings) >= 200:
                                break
                    if len(findings) >= 200:
                        break
                if path.name == "requirements.txt":
                    for name, version in re.findall(
                        r"^([\w.-]+)==([\w.+-]+)\s*$", text, re.M
                    ):
                        dependencies.append(("PyPI", name, version))
                if path.name == "package-lock.json":
                    import json

                    try:
                        lock = json.loads(text)
                        for name, item in lock.get("packages", {}).items():
                            if name.startswith("node_modules/") and item.get("version"):
                                dependencies.append(
                                    (
                                        "npm",
                                        name.removeprefix("node_modules/"),
                                        item["version"],
                                    )
                                )
                    except (ValueError, TypeError, AttributeError):
                        pass
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        raise HTTPException(422, "Invalid or unsupported ZIP file.")
    if not scanned:
        raise HTTPException(422, "No supported text source files were found.")
    osv = []
    if check_dependencies:
        for eco, name, version in list(dict.fromkeys(dependencies))[:10]:
            item = osv_query(eco, name, version)
            osv.append({"package": name, "version": version, **item})
    score = max(
        [{"critical": 90, "high": 65, "moderate": 35}[f["severity"]] for f in findings]
        or [0]
    )
    if any(item["ids"] for item in osv):
        score = max(score, 70)
    level = (
        "critical"
        if score >= 80
        else "high"
        if score >= 60
        else "moderate"
        if score >= 30
        else "low"
    )
    return {
        "score": score,
        "level": level,
        "status": "dangerous"
        if score >= 60
        else "suspicious"
        if score >= 30
        else "no_known_indicators",
        "summary": f"Static inspection completed for {scanned} text files. {len(findings)} potential findings require review.",
        "indicators": [
            {
                "code": f["code"] + "_" + str(i),
                "weight": 0,
                "reason": f"{f['file']}:{f['line']} — {f['code']} ({f['severity']}). {f['remediation']}",
            }
            for i, f in enumerate(findings)
        ],
        "details": {
            "findings": findings,
            "files_scanned": scanned,
            "osv": osv,
            "dependencies": [
                {"ecosystem": e, "name": n[:150], "version": v[:100]}
                for e, n, v in list(dict.fromkeys(dependencies))[:10]
            ],
        },
        "actions": [
            "Review each finding in context before changing code.",
            "Rotate exposed secrets; removing a line does not revoke a credential.",
        ],
        "urls": [],
        "provider": {
            "status": "local_static_rules",
            "reason": "Built-in static rules, not Semgrep, Bandit or Gitleaks. OSV runs only with explicit consent.",
        },
        "limitations": [
            "Pattern-based static review can miss vulnerabilities and produce false positives.",
            "Uploaded code was never executed. Original ZIP is discarded after processing.",
            "At most 200 findings and 10 exact-version dependencies checked. Unpinned dependencies are not verified.",
            "Risk uses the highest finding severity, not the number of matching lines.",
        ],
    }
