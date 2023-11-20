"""Run the full demo pipeline (spec section 04 entry point).

Usage:
    python scripts/run_demo.py --config configs/demo.json

Stages: generate synthetic data -> validate schema -> write manifest.
Later stages (reconstruction, prediction) are attached as they land.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lab_billing.schema.synthetic_generator import SyntheticGenerator  # noqa: E402
from lab_billing.schema import validator as v  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"run-{run_ts}-demo"
    out_dir = os.path.join(root, "outputs", "runs", run_id)
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    t0 = time.time()
    print(f"[run_demo] run_id={run_id}")
    gen = SyntheticGenerator(
        seed=cfg.get("seed", 42),
        n_lineages=cfg.get("demo_lineages", 1000),
        business_start="2022-07-01",
        as_of="2023-11-15",
    )
    gen.write(data_dir)
    print(f"[run_demo] synthetic data written to {data_dir}")

    findings: list[str] = []
    expected_dirty: list[str] = []
    for table, fn in (
        ("bills", v.validate_bills),
        ("events", v.validate_events),
        ("allocations", v.validate_allocations),
        ("observation_windows", v.validate_observation_windows),
    ):
        path = os.path.join(data_dir, f"{table}.csv")
        with open(path, encoding="utf-8") as f:
            res = fn(f.read())
        print(f"[run_demo] {res.report()}")
        for f_ in res.findings:
            if f_.severity != "ERROR":
                continue
            msg = f"{table}: {f_.row_ref} {f_.field} {f_.problem}"
            # Known injected dirt the validator is *supposed* to catch.
            if ("must be positive integer" in f_.problem
                    or "unsupported currency" in f_.problem
                    or "currency required with amount" in f_.problem
                    or "ISO 8601 with timezone" in f_.problem):
                expected_dirty.append(msg)
            else:
                findings.append(msg)

    print(f"[run_demo] expected dirty cases intercepted: {len(expected_dirty)}")
    receipt = {
        "run_id": run_id,
        "mode": "DEMO",
        "config": os.path.abspath(args.config),
        "generator_version": "0.1.0",
        "wall_clock_start": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t0, 2),
        "data_dir": data_dir,
        "schema_errors_unexpected": findings,
        "expected_dirty_intercepted": len(expected_dirty),
        "status": "OK" if not findings else "UNEXPECTED_SCHEMA_ERRORS",
    }
    with open(os.path.join(out_dir, "run_receipt.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print(f"[run_demo] receipt: {receipt['status']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
