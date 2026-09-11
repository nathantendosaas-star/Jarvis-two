"""
Single point of contact with OpenRouter. Nothing else in the codebase
should call requests.post directly -- keeps the API surface swappable
(e.g. if you ever want to switch models or providers).
"""

import ssl
import requests
from requests.adapters import HTTPAdapter

import config

# ── SSL fix for Python 3.14 (SSLEOFError / UNEXPECTED_EOF_WHILE_READING) ──
# Python 3.14 tightened TLS behaviour; some hosts (incl. OpenRouter) drop the
# connection before sending a close_notify alert. Mounting a custom adapter
# resolves this without disabling certificate verification.
try:
    from urllib3.util.ssl_ import create_urllib3_context

    class _TLSAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            kwargs["ssl_context"] = ctx
            super().init_poolmanager(*args, **kwargs)

    _SESSION = requests.Session()
    _SESSION.mount("https://", _TLSAdapter())
except Exception:
    _SESSION = requests.Session()

_SESSION.headers.update({
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "JARVIS AI OS",
})


def chat(messages, temperature=0.4):
    if not config.API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. See README.md for setup."
        )

    _SESSION.headers["Authorization"] = f"Bearer {config.API_KEY}"

    # reasoning is only supported by deepseek-r1, NOT by deepseek-v4-flash
    payload = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if "deepseek-r1" in config.MODEL:
        payload["reasoning"] = {"enabled": True}

    r = _SESSION.post(config.API_URL, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    choice = data["choices"][0]["message"]
    return {
        "content": choice.get("content") or "",
        "reasoning": choice.get("reasoning"),
    }
