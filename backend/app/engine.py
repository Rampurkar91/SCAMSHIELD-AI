"""Deterministic, explainable triage. Scores are estimates, never fraud probabilities.
No submitted URL is fetched: this avoids SSRF and accidental malicious navigation.
"""

import re
import ipaddress
from urllib.parse import urlsplit, parse_qs
from email import policy
from email.parser import Parser

ACTIONS = [
    "Do not share passwords, OTPs or your UPI PIN.",
    "Verify independently using an official app or a known contact number.",
    "If money was lost, contact your bank immediately and call 1930.",
]


def analyze(kind: str, content: str):
    evidence = {}
    urls = []
    details = {}

    def add(key, weight, reason):
        evidence.setdefault(key, {"code": key, "weight": weight, "reason": reason})

    def url_check(raw):
        raw = raw.rstrip(".,;)")
        parsed = urlsplit(raw)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Enter a complete http:// or https:// URL.")
        host = parsed.hostname.lower().rstrip(".")
        try:
            _ = parsed.port
            ascii_host = host.encode("idna").decode("ascii")
            if any(c.isspace() for c in raw) or not re.fullmatch(
                r"[a-zA-Z0-9.:-]+", ascii_host
            ):
                raise ValueError()
        except (ValueError, UnicodeError):
            raise ValueError("The URL has an invalid hostname or port.")
        urls.append(raw)
        if parsed.scheme == "http":
            add(
                "unencrypted",
                15,
                "HTTP does not encrypt the connection; HTTPS alone would not prove legitimacy.",
            )
        if parsed.username or parsed.password:
            add(
                "userinfo",
                30,
                "The URL contains a misleading username or password segment.",
            )
        try:
            ipaddress.ip_address(host)
            add(
                "ip_host",
                25,
                "The destination uses an IP address rather than a recognizable domain.",
            )
        except ValueError:
            pass
        if host in {"bit.ly", "tinyurl.com", "t.co", "shorturl.at"}:
            add(
                "shortener",
                20,
                "A shortened URL hides its final destination. Redirect resolution was not performed.",
            )
        if len(host.split(".")) > 4:
            add(
                "subdomains", 15, "Many subdomains can disguise the actual destination."
            )
        if host.startswith("xn--") or ".xn--" in host:
            add(
                "punycode",
                20,
                "An internationalized domain can visually resemble another domain.",
            )
        if host.endswith((".xyz", ".top", ".click", ".zip")):
            add(
                "tld",
                10,
                "This domain suffix warrants additional scrutiny; the suffix alone is not evidence of fraud.",
            )
        brands = ("paypal", "sbi", "hdfcbank", "icicibank", "google", "microsoft")
        official = (
            "paypal.com",
            "sbi.co.in",
            "onlinesbi.sbi",
            "hdfcbank.com",
            "icicibank.com",
            "google.com",
            "microsoft.com",
        )
        if any(b in host for b in brands) and not any(
            host == d or host.endswith("." + d) for d in official
        ):
            add(
                "brand_domain",
                30,
                "The domain contains a known brand name but is not one of its recognized domains. This is a heuristic, not a definitive ownership check.",
            )
        if any(
            k.lower() in {"redirect", "next", "url", "return", "continue"}
            and any(v.startswith(("http:", "https:", "//")) for v in vals)
            for k, vals in parse_qs(parsed.query).items()
        ):
            add(
                "redirect_param", 15, "A query parameter points to another destination."
            )
        details.update(domain=host, https=parsed.scheme == "https")

    if kind == "url":
        url_check(content.strip())
    else:
        text = content.lower()
        for match in re.findall(r'https?://[^\s<>"\]]+', content):
            try:
                url_check(match)
            except ValueError:
                pass

        # Negation/awareness context is not an instruction to disclose secrets.
        def is_educational(part):
            return bool(
                re.search(
                    r"(never|do not|don.t|कभी नहीं|शेअर करू नका|साझा न करें).{0,45}(otp|pin|password|ओटीपी|पिन)|(otp|pin|password|ओटीपी|पिन).{0,35}(शेअर करू नका|साझा न करें)",
                    part,
                )
            )

        clauses = re.split(r"[.!?;।\n]+", text)
        educational = all(is_educational(part) for part in clauses if part.strip())
        sensitive = r"(otp|upi\s*pin|password|ओटीपी|पिन|पासवर्ड)"
        request = r"(share|send|tell|enter|provide|भेज|बताएं|सांगा|पाठवा|द्या|दर्ज)"
        if any(
            not is_educational(part)
            and (
                re.search(request + r".{0,65}" + sensitive, part)
                or re.search(sensitive + r".{0,35}" + request, part)
            )
            for part in clauses
        ):
            add(
                "secret_request",
                55,
                "The message asks you to disclose or enter a sensitive credential. Verify the context independently.",
            )
        urgent = bool(
            re.search(r"urgent|immediately|within \d+|आज ही|ताबडतोब|तुरंत", text)
        )
        consequence = bool(re.search(r"block|suspend|kyc|arrest|बंद|गिरफ्तार", text))
        if urgent and consequence:
            add(
                "coercion",
                30,
                "An urgent deadline is combined with an account restriction or legal threat.",
            )
        reward = bool(re.search(r"cashback|refund|prize|lottery|won|इनाम|बक्षीस", text))
        payment = bool(
            re.search(r"pay|transfer|fee|deposit|collect|scan|upi|पैसे|भुगतान", text)
        )
        if reward and payment:
            add(
                "reward_payment",
                35,
                "A reward or refund is paired with payment instructions, a common advance-fee pattern.",
            )
        if (
            re.search(
                r"(receive|receiving|refund|पैसे मिळ|प्राप्त).{0,80}(pin|collect|scan)|(pin|collect).{0,80}(receive|refund)",
                text,
            )
            and not educational
        ):
            add(
                "receive_pin",
                45,
                "Instructions link receiving money with a PIN or collect approval. A UPI PIN normally authorizes money leaving your account.",
            )
        if re.search(r"guaranteed.{0,25}(return|profit)|double your money", text):
            add(
                "investment",
                35,
                "Guaranteed or unrealistic investment returns are a scam indicator.",
            )
        if kind == "email":
            message = Parser(policy=policy.default).parsestr(content)
            details["sender"] = str(message.get("From", "Not supplied"))
            details["subject"] = str(message.get("Subject", "Not supplied"))
            auth = str(message.get("Authentication-Results", ""))
            details["header_note"] = (
                "Pasted authentication headers are untrusted and were not independently verified."
            )
            if re.search(r"(spf|dkim|dmarc)=fail", auth, re.I):
                add(
                    "email_auth",
                    25,
                    "Supplied email headers report an authentication failure; headers can be forged.",
                )
    if kind == "upi":
        if "secret_request" in evidence:
            action = "Sharing or entering confidential information"
        elif re.search(r"collect|approve|मंजूर|स्वीकार", text):
            action = (
                "Approving a collect request may authorize money leaving your account"
            )
        elif re.search(r"pin|पिन", text) and not educational:
            action = "Entering a UPI PIN normally authorizes an outgoing payment"
        elif re.search(r"receive|received|प्राप्त|मिळ", text):
            action = "Describes receiving money; receipt is not independently verified"
        else:
            action = "Unclear payment instruction; verify independently"
        details["payment_action"] = action
    score = min(100, sum(x["weight"] for x in evidence.values()))
    level = (
        "critical"
        if score >= 80
        else "high"
        if score >= 60
        else "moderate"
        if score >= 30
        else "low"
    )
    return dict(
        score=score,
        level=level,
        status="dangerous"
        if score >= 60
        else "suspicious"
        if score >= 30
        else "no_known_indicators",
        indicators=list(evidence.values()),
        urls=list(dict.fromkeys(urls)),
        details=details,
        summary="Indicators requiring caution were found."
        if evidence
        else "No known indicators were detected by the local rules. This does not establish safety.",
        actions=ACTIONS,
        provider={
            "status": "not_checked",
            "reason": "External threat intelligence is not integrated in this phase.",
        },
        limitations=[
            "Heuristic risk estimate, not a probability or a guarantee.",
            "No domain age, redirects, website contents or bank transactions were verified.",
            "Context rules cover some English, Hindi and Marathi phrases; language coverage is incomplete.",
        ],
    )
