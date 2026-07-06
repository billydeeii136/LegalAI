#!/usr/bin/env python3
"""Provider query template for paid and free legal research integrations."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import requests

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "westlaw": {
        "provider_name": "westlaw",
        "url_env": "WESTLAW_API_URL",
        "key_env": "WESTLAW_API_KEY",
        "key_required": True,
        "method": "POST",
        "query_location": "json",
        "query_param": "query",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
    },
    "lexis": {
        "provider_name": "lexisnexis",
        "url_env": "LEXIS_API_URL",
        "key_env": "LEXIS_API_KEY",
        "key_required": True,
        "method": "POST",
        "query_location": "json",
        "query_param": "query",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
    },
    "courtlistener": {
        "provider_name": "courtlistener",
        "url_env": "COURTLISTENER_API_URL",
        "key_env": "COURTLISTENER_API_TOKEN",
        "key_required": False,
        "method": "GET",
        "query_location": "params",
        "query_param": "q",
        "auth_header": "Authorization",
        "auth_prefix": "Token",
    },
    "recap": {
        "provider_name": "recap",
        "url_env": "RECAP_API_URL",
        "key_env": "COURTLISTENER_API_TOKEN",
        "key_required": False,
        "method": "GET",
        "query_location": "params",
        "query_param": "q",
        "auth_header": "Authorization",
        "auth_prefix": "Token",
    },
    "govinfo": {
        "provider_name": "govinfo",
        "url_env": "GOVINFO_API_URL",
        "key_env": "GOVINFO_API_KEY",
        "key_required": True,
        "method": "GET",
        "query_location": "params",
        "query_param": "query",
        "auth_in": "query",
        "auth_query_param": "api_key",
    },
    "worldlii": {
        "provider_name": "worldlii",
        "url_env": "WORLDLII_SEARCH_URL",
        "key_required": False,
        "method": "GET",
        "query_location": "params",
        "query_param": "query",
    },
    "bailii": {
        "provider_name": "bailii",
        "url_env": "BAILII_SEARCH_URL",
        "key_required": False,
        "method": "GET",
        "query_location": "params",
        "query_param": "query",
    },
    "cornell_lii": {
        "provider_name": "cornell_lii",
        "url_env": "CORNELL_LII_SEARCH_URL",
        "key_required": False,
        "method": "GET",
        "query_location": "params",
        "query_param": "query",
    },
    "canlii": {
        "provider_name": "canlii",
        "url_env": "CANLII_API_URL",
        "key_env": "CANLII_API_KEY",
        "key_required": True,
        "method": "GET",
        "query_location": "params",
        "query_param": "query",
        "auth_header": "X-API-KEY",
        "auth_prefix": "",
    },
}


def _resolve_max_bytes() -> int:
    raw = os.getenv("MAX_PROVIDER_RESPONSE_BYTES", "4000").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 4000
    if parsed <= 0:
        return 4000
    return parsed


def _attach_auth(headers: dict, params: dict, spec: dict, key: str) -> None:
    if not key:
        return
    if spec.get("auth_in") == "query":
        params[spec.get("auth_query_param", "api_key")] = key
        return

    auth_header = spec.get("auth_header", "Authorization")
    auth_prefix = spec.get("auth_prefix")
    if auth_prefix is None or auth_prefix == "":
        headers[auth_header] = key
    else:
        headers[auth_header] = f"{auth_prefix} {key}"


def _query(provider_key: str, query: str) -> dict:
    spec = PROVIDERS[provider_key]
    provider_name = spec.get("provider_name", provider_key)
    url_env = spec["url_env"]
    key_env = spec.get("key_env", "")
    url = os.getenv(url_env, "").strip()
    key = os.getenv(key_env, "").strip() if key_env else ""

    if not url:
        return {
            "provider": provider_name,
            "configured": False,
            "message": f"Missing {url_env}",
        }

    if spec.get("key_required", False) and not key:
        return {
            "provider": provider_name,
            "configured": False,
            "message": f"Missing required credential {key_env}",
        }

    method = str(spec.get("method", "GET")).upper()
    query_location = spec.get("query_location", "params")
    query_param = spec.get("query_param", "q")
    headers = {"Accept": "application/json, text/plain;q=0.9, */*;q=0.8"}
    params: dict[str, str] = {}
    body_json = None
    body_data = None

    if query_location == "json":
        body_json = {query_param: query}
    elif query_location == "data":
        body_data = {query_param: query}
    else:
        params[query_param] = query

    _attach_auth(headers, params, spec, key)

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params or None,
            json=body_json,
            data=body_data,
            timeout=45,
        )
    except requests.RequestException as exc:
        return {
            "provider": provider_name,
            "configured": True,
            "request_method": method,
            "request_url": url,
            "request_error": str(exc),
        }

    max_bytes = _resolve_max_bytes()
    return {
        "provider": provider_name,
        "configured": True,
        "request_method": method,
        "request_url": url,
        "status_code": response.status_code,
        "body_preview": response.text[:max_bytes],
        "content_type": response.headers.get("content-type", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=tuple(sorted(PROVIDERS.keys())), required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    payload = _query(args.provider, args.query)
    json.dump(payload, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
