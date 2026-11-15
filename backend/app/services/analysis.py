from ..engine import analyze
from ..integrations.providers import check_url, gemini_answer
from .ml import predict_sms


def enrich(kind, content, external=False, ai=False, language="English"):
    result = analyze(kind, content)
    result["sources"] = ["local_rules"]
    result["providers"] = []
    if external:
        # Bound work and disclosure. URLs are sent to configured providers, never visited.
        from concurrent.futures import ThreadPoolExecutor

        jobs = [
            (name, url)
            for url in result["urls"][:3]
            for name in ("safe_browsing", "urlhaus", "phishtank", "virustotal")
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            result["providers"] = list(pool.map(lambda job: check_url(*job), jobs))
        matched = [p for p in result["providers"] if p["status"] == "matched"]
        if matched:
            result["score"] = max(result["score"], 90)
            result["level"] = "critical"
            result["status"] = "dangerous"
            result["indicators"].append(
                {
                    "code": "known_threat_match",
                    "weight": 0,
                    "reason": "Threat intelligence match establishes a minimum risk score of 90. Categories: "
                    + ", ".join(sorted(set(p["category"] for p in matched))),
                }
            )
            result["summary"] = (
                "One or more threat intelligence providers reported a match. Avoid the destination."
            )
        result["provider"] = {
            "status": "completed"
            if result["providers"]
            and all(
                p["status"] in ("matched", "no_match", "not_found")
                for p in result["providers"]
            )
            else "partial_or_unavailable",
            "reason": "See individual provider coverage. A missing match is not proof of safety.",
        }
    else:
        result["provider"] = {
            "status": "not_checked",
            "reason": "External URL checks were not requested. No destinations were visited.",
        }
    result["ml"] = (
        predict_sms(content)
        if kind in ("message", "upi")
        else {"status": "not_applicable"}
    )
    if result["ml"]["status"] == "ok":
        result["sources"].append("english_sms_spam_baseline")
    result["ai"] = (
        gemini_answer(content, language) if ai else {"status": "not_requested"}
    )
    if result["ai"]["status"] == "ok":
        result["sources"].append("ai_explanation")
    result["limitations"].append(
        "ML spam classification and AI explanations are separate advisory outputs and do not change the evidence-based score."
    )
    return result
