#!/usr/bin/env python3
"""Generates PACER query plans from legal case watchlists for agent/chatbot workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def _load_watchlist(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Watchlist file not found: {path}")

    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(raw) or {}
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass

    json_fallback = path.with_suffix(".json")
    if json_fallback.exists():
        return json.loads(json_fallback.read_text(encoding="utf-8"))

    raise SystemExit(
        "Unable to parse YAML watchlist. Install pyyaml (`pip install pyyaml`) or provide a .json watchlist."
    )


def _load_session(path: Path) -> dict:
    if not path.exists():
        return {"login_status": "unknown", "transport": "none"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"login_status": "unknown", "transport": "none"}

def _load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_cases(payload: dict) -> list[dict]:
    cases = []
    for bucket_name in ("federal_cases", "state_cases"):
        for entry in payload.get(bucket_name, []) or []:
            if not isinstance(entry, dict):
                continue
            cases.append(
                {
                    "bucket": bucket_name,
                    "case_title": entry.get("case_title", "UNKNOWN_TITLE"),
                    "court": str(entry.get("court", "unknown")).lower(),
                    "case_number": str(entry.get("case_number", "unknown")),
                    "tags": entry.get("tags", []),
                    "automation": entry.get("automation", {}),
                }
            )
    return cases

def _normalize_court_label(raw: str) -> str:
    text = raw.strip().lower()
    mapping = {
        "nced": "usdc-ednc",
        "ednc": "usdc-ednc",
        "usdc-ednc": "usdc-ednc",
        "vaed": "usdc-edva",
        "edva": "usdc-edva",
        "usdc-edva": "usdc-edva",
        "uscoa-4": "uscoa-4",
        "4th-circuit": "uscoa-4",
        "fourth-circuit": "uscoa-4",
        "4th circuit": "uscoa-4",
    }
    return mapping.get(text, text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", required=True)
    parser.add_argument("--session-in", required=True)
    parser.add_argument("--report-out", required=True)
    parser.add_argument("--identity-anchors", required=False)
    parser.add_argument("--drive-discovered", required=False)
    args = parser.parse_args()

    watchlist_path = Path(args.watchlist)
    session_path = Path(args.session_in)
    report_path = Path(args.report_out)
    identity_anchor_path = (
        Path(args.identity_anchors) if args.identity_anchors else watchlist_path.parent / "LEGAL_IDENTITY_ANCHORS.yaml"
    )
    drive_discovered_path = (
        Path(args.drive_discovered)
        if args.drive_discovered
        else watchlist_path.parent / "DRIVE_DISCOVERED_CASE_ANCHORS.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    watchlist = _load_watchlist(watchlist_path)
    session = _load_session(session_path)
    drive_discovered_payload = _load_optional_json(drive_discovered_path)
    cases = _normalize_cases(watchlist)

    queued = []
    skipped = []
    pacer_federal_targets = {"usdc-ednc", "usdc-edva", "uscoa-4"}
    for case in cases:
        automation = case.get("automation", {})
        pacer_enabled = bool(automation.get("pacer_enabled"))
        court_normalized = _normalize_court_label(case["court"])
        if pacer_enabled and case["bucket"] == "federal_cases" and court_normalized in pacer_federal_targets:
            queued.append(
                {
                    "case_title": case["case_title"],
                    "court": court_normalized,
                    "case_number": case["case_number"],
                    "case_number_aliases": case.get("case_number_aliases", []),
                    "query_type": "pacer_case_lookup",
                }
            )
        else:
            skipped.append(
                {
                    "case_title": case["case_title"],
                    "court": court_normalized,
                    "case_number": case["case_number"],
                    "reason": "non-federal_or_pacer_disabled",
                }
            )

    report = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "watchlist_file": str(watchlist_path),
        "session_file": str(session_path),
        "identity_anchor_file": str(identity_anchor_path),
        "identity_anchor_exists": identity_anchor_path.exists(),
        "drive_discovered_file": str(drive_discovered_path),
        "drive_discovered_exists": drive_discovered_path.exists(),
        "drive_discovered_case_anchor_count": (
            drive_discovered_payload.get("case_anchor_count") if drive_discovered_payload else 0
        ),
        "pacer_federal_targets": sorted(pacer_federal_targets),
        "session_status": session.get("login_status", "unknown"),
        "session_transport": session.get("transport", "unknown"),
        "total_cases": len(cases),
        "queued_pacer_queries": queued,
        "skipped_cases": skipped,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote PACER case sync report to {report_path}")


if __name__ == "__main__":
    main()
