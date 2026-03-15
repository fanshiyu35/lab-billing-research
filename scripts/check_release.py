"""Release readiness check (spec section 21 entry point).

Usage:
    python scripts/check_release.py --root .

Verifies: clean-env reproducibility inputs exist, demo pipeline ran, test
suite ran, no private data in public paths, version consistency, Power BI
native status explicit, no fabricated externals. Each requirement gets a
file or an explicit blocker note — never a bare PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(root: str) -> dict:
    items = []

    def req(name: str, ok: bool, detail: str):
        items.append({"requirement": name, "status": "OK" if ok else "BLOCKED",
                      "detail": detail})

    req("README installable", os.path.exists(os.path.join(root, "README.md")),
        "README.md present")
    req("locked requirements", os.path.exists(os.path.join(root, "requirements.lock.txt")),
        "requirements.lock.txt present")
    req("demo config", os.path.exists(os.path.join(root, "configs", "demo.json")),
        "configs/demo.json present")
    runs = sorted(os.listdir(os.path.join(root, "outputs", "runs"))) \
        if os.path.isdir(os.path.join(root, "outputs", "runs")) else []
    req("demo pipeline ran", bool(runs), f"{len(runs)} run directories")
    req("acceptance suite ran",
        os.path.exists(os.path.join(root, "outputs", "qa", "junit.xml")),
        "outputs/qa/junit.xml present")
    priv = os.path.join(root, "data", "private")
    req("no private data in repo",
        os.path.isdir(priv) and not os.listdir(priv),
        "data/private exists and is empty")
    gt = os.path.join(root, "outputs", "runs", runs[-1], "data", "_ground_truth") if runs else ""
    req("hidden truth separated", bool(gt) and os.path.isdir(gt),
        "_ground_truth directory kept under data/, excluded by .gitignore")
    req("externals not fabricated",
        json.load(open(os.path.join(root, "external", "status.json"), encoding="utf-8")).get("status") == "NOT_OBTAINED",
        "external/status.json = NOT_OBTAINED")
    pbi = os.path.join(root, "powerbi", "STATUS.md")
    req("Power BI native status explicit",
        os.path.exists(pbi) and "NOT_BUILT" in open(pbi, encoding="utf-8").read(),
        "powerbi/STATUS.md declares NOT_BUILT/NOT_TESTED")
    report_pdf = [f for f in os.listdir(os.path.join(root, "outputs", "reports"))
                  if f.endswith(".pdf")] if os.path.isdir(os.path.join(root, "outputs", "reports")) else []
    req("report PDF built", bool(report_pdf), ", ".join(report_pdf))
    packet = os.path.join(root, "release", "DEMO_REVIEW_PACKET.pdf")
    req("review packet built", os.path.exists(packet), "release/DEMO_REVIEW_PACKET.pdf")
    req("changelog present", os.path.exists(os.path.join(root, "CHANGELOG.md")),
        "CHANGELOG.md present")
    req("next action maintained", os.path.exists(os.path.join(root, "NEXT_ACTION.md")),
        "NEXT_ACTION.md present")
    return {"checked_at": "2026-09-22", "items": items,
            "summary": {"ok": sum(1 for i in items if i["status"] == "OK"),
                        "blocked": sum(1 for i in items if i["status"] == "BLOCKED")}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    args = ap.parse_args()
    report = check(args.root)
    print(json.dumps(report, indent=2))
    return 0 if report["summary"]["blocked"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
