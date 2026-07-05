#!/usr/bin/env python3
"""PACER login automation template with secure credential sourcing and MFA handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import subprocess
import time
from pathlib import Path

import requests


def _extract_hidden_inputs(html: str) -> dict[str, str]:
    pairs = re.findall(
        r'<input[^>]*type=["\\\']hidden["\\\'][^>]*name=["\\\']([^"\\\']+)["\\\'][^>]*value=["\\\']([^"\\\']*)["\\\']',
        html,
        flags=re.IGNORECASE,
    )
    return {name: value for name, value in pairs}


def _read_keychain_password(service: str, account: str) -> str:
    if platform.system() != "Darwin":
        return ""
    command = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        command.extend(["-a", account])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _load_credentials() -> tuple[str, str, str]:
    username = os.getenv("PACER_USERNAME", "").strip()
    keychain_account = os.getenv("PACER_KEYCHAIN_ACCOUNT", "").strip()
    if not username and keychain_account:
        username = keychain_account

    password = os.getenv("PACER_PASSWORD", "").strip()
    keychain_service = os.getenv("PACER_KEYCHAIN_SERVICE", "").strip()
    if not password and keychain_service:
        password = _read_keychain_password(keychain_service, keychain_account or username)

    client_code = os.getenv("PACER_CLIENT_CODE", "HARVEY_LEGAL_AUTOMATION").strip()

    if not username or not password:
        raise SystemExit(
            "Missing PACER credentials. Set PACER_USERNAME/PACER_PASSWORD or PACER_KEYCHAIN_SERVICE (+ PACER_KEYCHAIN_ACCOUNT)."
        )
    return username, password, client_code


def _requests_login(
    *,
    login_url: str,
    username: str,
    password: str,
    client_code: str,
) -> dict:
    session = requests.Session()
    page = session.get(login_url, timeout=45)
    page.raise_for_status()

    payload = _extract_hidden_inputs(page.text)
    payload.update(
        {
            "login": username,
            "password": password,
            "clientCode": client_code,
        }
    )

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
    return {
        "transport": "requests",
        "login_status": "failed" if login_failed else "submitted_or_authenticated",
        "cookie_names": [cookie.name for cookie in session.cookies],
    }


def _page_logged_in(page) -> bool:
    url = page.url.lower()
    if "csologin" not in url and "login" not in url:
        return True
    content = page.content().lower()
    return any(token in content for token in ("logout", "sign out", "my account", "case search"))


def _fill_first(page, selectors: list[str], value: str) -> bool:
    for selector in selectors:
        node = page.query_selector(selector)
        if node:
            node.fill(value)
            return True
    return False


def _click_first(page, selectors: list[str]) -> bool:
    for selector in selectors:
        node = page.query_selector(selector)
        if node:
            node.click()
            return True
    return False


def _playwright_login(
    *,
    login_url: str,
    username: str,
    password: str,
    client_code: str,
    state_out: Path,
    mfa_timeout_seconds: int,
    headless: bool,
) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url, wait_until="domcontentloaded", timeout=90_000)

        user_ok = _fill_first(
            page,
            [
                "input[name='login']",
                "input[name='username']",
                "input[id*='user']",
                "input[type='email']",
                "input[type='text']",
            ],
            username,
        )
        pass_ok = _fill_first(
            page,
            [
                "input[name='password']",
                "input[id*='pass']",
                "input[type='password']",
            ],
            password,
        )
        if client_code:
            _fill_first(
                page,
                [
                    "input[name='clientCode']",
                    "input[id*='client']",
                ],
                client_code,
            )

        if not user_ok or not pass_ok:
            browser.close()
            raise RuntimeError("Unable to locate PACER username/password inputs in browser flow.")

        submit_clicked = _click_first(
            page,
            [
                "button[type='submit']",
                "input[type='submit']",
                "button[name='login']",
                "button:has-text('Login')",
            ],
        )
        if not submit_clicked:
            page.keyboard.press("Enter")

        page.wait_for_timeout(1_500)

        mfa_required = not _page_logged_in(page)
        if mfa_required:
            deadline = time.time() + max(mfa_timeout_seconds, 30)
            while time.time() < deadline:
                if _page_logged_in(page):
                    mfa_required = False
                    break
                time.sleep(3)

        state_out.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(state_out))
        cookie_names = [cookie.get("name", "") for cookie in context.cookies()]
        status = "authenticated" if not mfa_required and _page_logged_in(page) else "mfa_pending_or_timeout"
        browser.close()
        return {
            "transport": "playwright",
            "login_status": status,
            "cookie_names": cookie_names,
            "storage_state_file": str(state_out),
            "mfa_required": mfa_required,
            "headless": headless,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--session-out", required=True)
    parser.add_argument(
        "--state-out",
        default=os.getenv("PACER_STORAGE_STATE_PATH", ".harvey/runtime/pacer_storage_state.json"),
    )
    parser.add_argument("--mode", choices=("auto", "browser", "requests"), default=os.getenv("PACER_LOGIN_MODE", "auto"))
    parser.add_argument(
        "--mfa-timeout-seconds",
        type=int,
        default=int(os.getenv("PACER_MFA_TIMEOUT_SECONDS", "300")),
    )
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    username, password, client_code = _load_credentials()
    login_url = os.getenv("PACER_LOGIN_URL", "https://pacer.login.uscourts.gov/csologin/login.jsf")
    watchlist_path = Path(args.watchlist)
    session_path = Path(args.session_out)
    state_out = Path(args.state_out)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    headless = args.headless or os.getenv("PACER_HEADLESS", "0") == "1"
    runtime_note = None

    if args.mode in ("auto", "browser"):
        try:
            login_result = _playwright_login(
                login_url=login_url,
                username=username,
                password=password,
                client_code=client_code,
                state_out=state_out,
                mfa_timeout_seconds=args.mfa_timeout_seconds,
                headless=headless,
            )
        except Exception as exc:
            if args.mode == "browser":
                raise
            runtime_note = f"Browser flow unavailable, falling back to requests flow: {exc.__class__.__name__}"
            login_result = _requests_login(
                login_url=login_url,
                username=username,
                password=password,
                client_code=client_code,
            )
    else:
        login_result = _requests_login(
            login_url=login_url,
            username=username,
            password=password,
            client_code=client_code,
        )

    metadata = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "login_url": login_url,
        "username_hint": f"{username[:2]}***",
        "watchlist_file": str(watchlist_path),
        "watchlist_exists": watchlist_path.exists(),
        "mfa_mode": os.getenv("PACER_MFA_MODE", "manual"),
        "note": "MFA bypass is intentionally not implemented. Complete MFA prompts when required.",
        **login_result,
    }
    if runtime_note:
        metadata["runtime_note"] = runtime_note

    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote PACER session metadata to {session_path}")


if __name__ == "__main__":
    main()
