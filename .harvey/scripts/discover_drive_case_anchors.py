#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOTS = [
    "/Users/billydeeii136/Library/CloudStorage/GoogleDrive-billydeeii136@gmail.com/My Drive",
    "/Users/billydeeii136/Library/CloudStorage/GoogleDrive-williamscottdavis136@gmail.com/My Drive",
]

FEDERAL_CASE_PATTERN = re.compile(r"\b\d{1,2}:\d{2}-[Cc][Rr]-\d+\b|\b\d{1,2}:\d{2}-[Cc][Vv]-\d+\b")
STATE_CASE_PATTERN = re.compile(r"\b\d{2}-[Cc][Rr][Ss]-\d+\b")
USCOA4_DOCKET_PATTERN = re.compile(r"\b\d{2}-\d{4}\b")
NAME_PATTERN = re.compile(r"william\s+scott\s+davis\s*(jr|ii|2nd)?", re.IGNORECASE)


def infer_court(blob: str) -> str:
    text = blob.lower()
    if "4th circuit" in text or "court of appeals" in text or "uscoa" in text:
        return "USCOA-4"
    if "eastern district of virginia" in text or "edva" in text or "newport news" in text:
        return "USDC-EDVA"
    if "eastern district of north carolina" in text or "ednc" in text or "5:14-cr-240" in text:
        return "USDC-EDNC"
    if "crs-" in text:
        return "NC-STATE"
    return "UNKNOWN"


def iter_files_bounded(root: str, max_depth: int):
    root = os.path.abspath(root)
    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            yield entry.path
                        elif entry.is_dir(follow_symlinks=False) and depth < max_depth:
                            stack.append((entry.path, depth + 1))
                    except OSError:
                        continue
        except OSError:
            continue


def discover(max_files: int = 120000, max_depth: int = 6) -> dict:
    roots = [root for root in ROOTS if os.path.isdir(root)]
    scanned_files = 0
    scan_limited = False
    anchors: dict[tuple[str, str], list[str]] = {}
    name_hits: list[str] = []


    for root in roots:
        for full_path in iter_files_bounded(root, max_depth=max_depth):
            scanned_files += 1
            if scanned_files > max_files:
                scan_limited = True
                break

            filename = os.path.basename(full_path)
            rel_path = os.path.relpath(full_path, root)
            blob = f"{filename} {rel_path}"

            numbers = set(match.upper() for match in FEDERAL_CASE_PATTERN.findall(blob))
            numbers.update(match.upper() for match in STATE_CASE_PATTERN.findall(blob))
            if any(token in blob.lower() for token in ("4th circuit", "court of appeals", "uscoa")):
                numbers.update(USCOA4_DOCKET_PATTERN.findall(blob))

            if NAME_PATTERN.search(blob):
                name_hits.append(full_path)

            court = infer_court(blob)
            for number in numbers:
                anchors.setdefault((number, court), []).append(full_path)
        if scan_limited:
            break

    case_anchors = [
        {
            "case_number": number,
            "court": court,
            "sample_files": files[:3],
        }
        for (number, court), files in sorted(anchors.items())
    ]

    return {
        "roots": roots,
        "scanned_files": scanned_files,
        "scan_limited": scan_limited,
        "case_anchor_count": len(case_anchors),
        "case_anchors": case_anchors,
        "name_variant_hit_count": len(name_hits),
        "name_variant_samples": name_hits[:40],
    }


def main() -> None:
    max_files = int(os.getenv("DRIVE_ANCHOR_MAX_FILES", "2000"))
    max_depth = int(os.getenv("DRIVE_ANCHOR_MAX_DEPTH", "1"))
    summary = discover(max_files=max_files, max_depth=max_depth)
    output_path = Path("/Users/billydeeii136/harvey-template/DRIVE_DISCOVERED_CASE_ANCHORS.json")
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    print(
        json.dumps(
            {
                "roots": len(summary["roots"]),
                "scanned_files": summary["scanned_files"],
                "max_depth": max_depth,
                "case_anchor_count": summary["case_anchor_count"],
                "name_variant_hit_count": summary["name_variant_hit_count"],
                "scan_limited": summary["scan_limited"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
