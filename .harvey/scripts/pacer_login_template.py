#!/usr/bin/env python3
"""PACER login automation template.
This is a secure starter script: it does not bypass MFA and does not persist secrets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

import requests


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    pairs = re.findall(
        r'<input[^>]*type=["\\\']hidden["\\\'][^>]*name=["\\\']([^"\\\']+)["\\\'][^>]*value=["\\\']([^"\\\']*)["\\\']',
        html,
        flags=re.IGNORECASE,
    )
    return {name: value for name, value in pairs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--session-out", required=True)
    args = parser.parse_args()

    username = _require_env("PACER_USERNAME")
    password = _require_env("PACER_PASSWORD")
    login_url = os.getenv(
        "PACER_LOGIN_URL",
        "https://pacer.login.uscourts.gov/csologin/login.jsf",
    )

    session = requests.Session()
    page = session.get(login_url, timeout=45)
    page.raise_for_status()

    payload = _extract_hidden_inputs(page.text)
    payload.update(
        {
            "login": username,
            "password": password,
            "clientCode": os.getenv("PACER_CLIENT_CODE", "HARVEY_LEGAL_AUTOMATION"),
        }
    )

    # PACER field names can vary. Adjust payload keys to your exact login form if required.
    response = session.post(login_url, data=payload, timeout=45, allow_redirects=True)
    response.raise_for_status()

    body = response.text.lower()
    login_failed = any(
        marker in body
        for marker in (
            "invalid",
            "incorrect",
            "authentication failed",
        )
    )

    watchlist_path = Path(args.watchlist)
    session_path = Path(args.session_out)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "login_url": login_url,
        "username_hint": f"{username[:2]}***",
        "watchlist_file": str(watchlist_path),
        "watchlist_exists": watchlist_path.exists(),
        "cookie_names": [cookie.name for cookie in session.cookies],
        "mfa_mode": os.getenv("PACER_MFA_MODE", "manual"),
        "login_status": "failed" if login_failed else "submitted_or_authenticated",
        "note": "If MFA is enabled, complete the challenge in browser flow before protected actions.",
    }
    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote PACER session metadata to {session_path}")


if __name__ == "__main__":
    main()
