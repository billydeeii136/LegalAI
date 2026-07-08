#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path


RUNTIME_DIR = Path("/Users/billydeeii136/LegalAI/.harvey/runtime")
DRIVE_ROOT = Path("/Users/billydeeii136/Library/CloudStorage/GoogleDrive-billydeeii136@gmail.com/My Drive")
DRIVE_DIR = DRIVE_ROOT / "LegalAI-Node-Status"

REPOS = [
    "/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-agents",
    "/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-core",
    "/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-domains",
    "/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-inventory",
    "/Users/billydeeii136/WSD_CCOS/repos/wsd-ccos-legal",
    "/Users/billydeeii136/LegalAI",
    "/Users/billydeeii136/lawSystem",
    "/Users/billydeeii136/lawyergpt",
    "/Users/billydeeii136/lawyersongithub",
    "/Users/billydeeii136/Robot-Lawyer",
    "/Users/billydeeii136/robo-lawyer",
]


def run(cmd: list[str], cwd: str | None = None, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def detect_latest_device_report(runtime_dir: Path) -> Path | None:
    reports = sorted(runtime_dir.glob("push_legal_bundle_report_*.tsv"), key=lambda p: p.stat().st_mtime)
    return reports[-1] if reports else None


def collect_repo_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for repo in REPOS:
        print(f"[repo] {repo}", flush=True)
        git_dir = Path(repo) / ".git"
        if not git_dir.exists():
            rows.append(
                {
                    "node_path": repo,
                    "node_type": "local_repo",
                    "git_present": "no",
                    "branch": "missing",
                    "tracking": "none",
                    "remotes": "none",
                    "working_tree_state": "missing_repo",
                }
            )
            continue

        _, branch = run(["git", "--no-pager", "branch", "--show-current"], cwd=repo)
        rc_tracking, tracking = run(
            ["git", "--no-pager", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=repo,
        )
        if rc_tracking != 0 or not tracking:
            tracking = "none"

        _, remotes_raw = run(["git", "remote"], cwd=repo)
        remotes = ",".join([line for line in remotes_raw.splitlines() if line]) or "none"

        rc_status, status_raw = run(["git", "--no-pager", "status", "--short"], cwd=repo)
        if rc_status == 124:
            wt_state = "unknown:status_timeout"
        else:
            dirty = len([ln for ln in status_raw.splitlines() if ln.strip()])
            wt_state = "clean" if dirty == 0 else f"dirty:{dirty}"

        rows.append(
            {
                "node_path": repo,
                "node_type": "local_repo",
                "git_present": "yes",
                "branch": branch or "unknown",
                "tracking": tracking,
                "remotes": remotes,
                "working_tree_state": wt_state,
            }
        )
    return rows


def write_reports(
    runtime_dir: Path, device_report: Path | None, rows: list[dict[str, str]]
) -> tuple[Path, Path, Path]:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    local_tsv = runtime_dir / f"local_node_status_{timestamp}.tsv"
    consolidated_txt = runtime_dir / f"consolidated_node_status_{timestamp}.txt"
    consolidated_json = runtime_dir / f"consolidated_node_status_{timestamp}.json"

    with local_tsv.open("w", encoding="utf-8") as f:
        f.write("node_path\tnode_type\tgit_present\tbranch\ttracking\tremotes\tworking_tree_state\n")
        for row in rows:
            f.write(
                "\t".join(
                    [
                        row["node_path"],
                        row["node_type"],
                        row["git_present"],
                        row["branch"],
                        row["tracking"],
                        row["remotes"],
                        row["working_tree_state"],
                    ]
                )
                + "\n"
            )

    with consolidated_txt.open("w", encoding="utf-8") as f:
        f.write(f"timestamp_utc={dt.datetime.now(dt.timezone.utc).isoformat()}\n")
        f.write(f"device_report={device_report if device_report else 'none'}\n")
        f.write(f"local_report={local_tsv}\n\n")
        f.write("=== DEVICE STATUS ===\n")
        if device_report and device_report.exists():
            f.write(device_report.read_text(encoding="utf-8"))
        else:
            f.write("no_device_report_found\n")
        f.write("\n=== LOCAL NODE STATUS ===\n")
        f.write(local_tsv.read_text(encoding="utf-8"))

    payload = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "device_report": str(device_report) if device_report else None,
        "local_report": str(local_tsv),
        "nodes": rows,
    }
    consolidated_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return local_tsv, consolidated_txt, consolidated_json


def copy_to_drive(local_tsv: Path, consolidated_txt: Path, consolidated_json: Path, device_report: Path | None) -> None:
    if not DRIVE_ROOT.exists():
        return
    DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_tsv, DRIVE_DIR / local_tsv.name)
    shutil.copy2(consolidated_txt, DRIVE_DIR / consolidated_txt.name)
    shutil.copy2(consolidated_json, DRIVE_DIR / consolidated_json.name)
    if device_report and device_report.exists():
        shutil.copy2(device_report, DRIVE_DIR / device_report.name)


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    print("[start] collecting node status", flush=True)
    device_report = detect_latest_device_report(RUNTIME_DIR)
    rows = collect_repo_rows()
    print("[progress] writing reports", flush=True)
    local_tsv, consolidated_txt, consolidated_json = write_reports(RUNTIME_DIR, device_report, rows)
    print("[progress] copying reports to drive if available", flush=True)
    copy_to_drive(local_tsv, consolidated_txt, consolidated_json, device_report)

    print(f"LOCAL_REPORT={local_tsv}")
    print(f"CONSOLIDATED_TXT={consolidated_txt}")
    print(f"CONSOLIDATED_JSON={consolidated_json}")
    print(f"DEVICE_REPORT={device_report if device_report else 'none'}")
    print(consolidated_txt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
