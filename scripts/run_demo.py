"""Run the full pipeline (spec section 04 entry point).

Usage:
    python scripts/run_pipeline.py --config configs/reference.json

Stages: prepare data -> validate schema -> write manifest.
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

from lab_billing.schema.data_preparation import DataPreparationPipeline  # noqa: E402
from lab_billing.schema import validator as v  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data-dir", default=None,
                    help="optional: run on an existing mapped dataset "
                         "(external validation entry) instead of preparing data")
    ap.add_argument("--as-of", default="2023-11-15T00:00:00Z",
                    help="point-in-time cutoff for reconstruction")
    ap.add_argument("--run-id", default=None,
                    help="optional explicit run id (historical run bookkeeping)")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"run-{run_ts}"
    out_dir = os.path.join(root, "outputs", "runs", run_id)
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    t0 = time.time()
    print(f"[run_demo] run_id={run_id}")
    external_data = False
    if args.data_dir:
        src_data = os.path.abspath(args.data_dir)
        external_data = True
        print(f"[run_demo] external mapped dataset: {src_data}")
        # copy mapped inputs into the run dir (runs stay self-contained)
        import shutil as _shutil
        for f in os.listdir(src_data):
            if f.endswith((".csv", ".json")):
                _shutil.copy(os.path.join(src_data, f), os.path.join(data_dir, f))
        if os.path.isdir(os.path.join(src_data, "_ground_truth")):
            _shutil.copytree(os.path.join(src_data, "_ground_truth"),
                             os.path.join(data_dir, "_ground_truth"), dirs_exist_ok=True)
    else:
        gen = DataPreparationPipeline(
            seed=cfg.get("seed", 42),
            n_lineages=cfg.get("n_lineages", 1000),
            business_start="2022-07-01",
            as_of="2023-11-15",
        )
        gen.write(data_dir)
        print(f"[run_demo] data prepared at {data_dir}")

    # for external datasets, allow org/payer tokens present in the data
    import csv as _csv
    extra_orgs, extra_payers = set(), set()
    if external_data:
        try:
            with open(os.path.join(data_dir, "bills.csv"), encoding="utf-8") as _f:
                for _r in _csv.DictReader(_f):
                    extra_orgs.add(_r.get("org_token", ""))
                    extra_payers.add(_r.get("payer_token", ""))
        except FileNotFoundError:
            pass
        extra_orgs -= set(v._ORG_OK_DEFAULT)
        extra_payers -= set(v._PAYER_OK_DEFAULT)

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
            if external_data:
                res = fn(f.read(), extra_orgs=extra_orgs,
                         extra_payers=extra_payers) if table in ("bills", "events") \
                    else fn(f.read(), extra_orgs=extra_orgs)
            else:
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
        "mode": "STUDY",
        "config": os.path.abspath(args.config),
        "data_preparation_version": "0.1.0",
    "run_id_source": "explicit" if args.run_id else "wall_clock",
        "wall_clock_start": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t0, 2),
        "data_dir": data_dir,
        "schema_errors_unexpected": findings,
        "expected_dirty_intercepted": len(expected_dirty),
        "status": "OK" if not findings else "UNEXPECTED_SCHEMA_ERRORS",
    }
    # module A: reconstruction
    from lab_billing.reconstruct import ReconstructionEngine
    a_dir = os.path.join(out_dir, "module_a")
    eng = ReconstructionEngine(run_id=f"{run_id}-A",
                               as_of=args.as_of,
                               method_version="1.0.0")
    a_audit = eng.run(data_dir, a_dir)
    print(f"[run_demo] module A: {a_audit['summary']['lineages']} lineages, "
          f"{a_audit['summary']['links']} links")

    # module B: forecast
    from lab_billing.forecast import ForecastPipeline
    b_dir = os.path.join(out_dir, "module_b")
    fp = ForecastPipeline(run_id=f"{run_id}-B", interval_days=cfg.get("prediction", {}).get("interval_days", 5))
    b_report = fp.run(a_dir, b_dir)
    print(f"[run_demo] module B: {b_report['n_snapshots']} snapshots, "
          f"models={list(b_report['models'])}")

    receipt["module_a_summary"] = a_audit["summary"]
    receipt["module_b_summary"] = {
        k: v for k, v in b_report.items() if k in ("n_snapshots", "n_interval_rows", "models")
    }
    with open(os.path.join(out_dir, "run_receipt.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print(f"[run_demo] receipt: {receipt['status']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
