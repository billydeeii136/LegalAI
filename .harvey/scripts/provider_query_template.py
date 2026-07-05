#!/usr/bin/env python3
"""Provider query template for Westlaw/Lexis integrations."""

from __future__ import annotations

import argparse
import json
import os
import sys

import requests


def _query(name: str, url_env: str, key_env: str, query: str) -> dict:
    url = os.getenv(url_env, "").strip()
    key = os.getenv(key_env, "").strip()
    if not url or not key:
        return {
            "provider": name,
            "configured": False,
            "message": f"Missing {url_env} or {key_env}",
        }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=45,
    )
    return {
        "provider": name,
        "configured": True,
        "status_code": response.status_code,
        "body_preview": response.text[:4000],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("westlaw", "lexis"), required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    if args.provider == "westlaw":
        payload = _query("westlaw", "WESTLAW_API_URL", "WESTLAW_API_KEY", args.query)
    else:
        payload = _query("lexisnexis", "LEXIS_API_URL", "LEXIS_API_KEY", args.query)

    json.dump(payload, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
