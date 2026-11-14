"""Read-only public GitHub archive retrieval. Fixed hosts, no git hooks or execution."""

import re
from urllib.parse import quote
import httpx
from fastapi import HTTPException
from .code import scan_zip


def scan_github(url, check_dependencies=False):
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9_-]{1,100})/([A-Za-z0-9_.-]{1,100})/?", url
    )
    if not match:
        raise HTTPException(
            422,
            "Use an HTTPS github.com owner/repository URL, without query or fragment.",
        )
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if repo in (".", "..", ""):
        raise HTTPException(422, "Invalid repository name.")
    try:
        with httpx.Client(
            timeout=15,
            follow_redirects=False,
            headers={
                "User-Agent": "ScamShieldAI-readonly",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            response = client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if response.status_code == 404:
                raise HTTPException(
                    404,
                    "Public repository not found. Private repositories are not supported.",
                )
            if response.status_code in (403, 429):
                raise HTTPException(
                    503, "GitHub access or rate limit prevented this scan."
                )
            response.raise_for_status()
            metadata = response.json()
            if metadata.get("private") or not isinstance(
                metadata.get("default_branch"), str
            ):
                raise HTTPException(
                    422, "Only public repositories with a default branch are supported."
                )
            # Pin the archive to a resolved immutable commit, not an untrusted redirect.
            commit_response = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{quote(metadata['default_branch'], safe='')}"
            )
            commit_response.raise_for_status()
            sha = commit_response.json()["sha"]
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise ValueError()
            with client.stream(
                "GET", f"https://codeload.github.com/{owner}/{repo}/zip/{sha}"
            ) as archive:
                archive.raise_for_status()
                raw = bytearray()
                for chunk in archive.iter_bytes(65536):
                    raw.extend(chunk)
                    if len(raw) > 5 * 1024 * 1024:
                        raise HTTPException(
                            413,
                            "Repository archive exceeds 5 MiB; upload a smaller source ZIP instead.",
                        )
        result = scan_zip(bytes(raw), check_dependencies)
        result["details"].update(repository=f"{owner}/{repo}", commit=sha)
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(
            503, "GitHub retrieval failed. No repository analysis was completed."
        )
