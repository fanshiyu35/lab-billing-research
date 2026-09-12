"""Generate an external-organization validation scenario dataset.

Creates a single-organization dataset (org_token = the organization, three
internal source systems) from the study data generator, remaps tokens and
timestamps to the organization's own timezone, and derives adjudicated
reference pairs from same-bill version chains.

Usage:
    python scripts/gen_org_scenario.py --org WCP --seed 7 --n-lineages 1200 \
        --tz America/Chicago --run-id run-WCP-20260910T000000Z
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lab_billing.schema.data_preparation import DataPreparationPipeline  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# generator source system -> organization internal system name
SOURCE_MAP_TEMPLATE = {
    "CPL_BILLING": "{ORG}_CLAIMS",
    "CPL_BILLING_LEGACY": "{ORG}_CLAIMS_LEGACY",
    "NDX_BILLING": "{ORG}_LIS",
    "NDX_BILLING_LEGACY": "{ORG}_LIS_LEGACY",
    "TRI_BILLING": "{ORG}_OR_BILLING",
    "TRI_BILLING_LEGACY": "{ORG}_OR_BILLING_LEGACY",
}


def _shift_tz(value: str, tz_name: str) -> str:
    """Re-render a timestamp in the organization's local timezone."""
    if not value or value.strip() == "":
        return value
    v = value.strip()
    try:
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo(tz_name)).isoformat(timespec="seconds")
    except ValueError:
        return value


def _fix_time_columns(row: dict, tz: str, cols: tuple[str, ...]) -> dict:
    for c in cols:
        if c in row and row[c]:
            row[c] = _shift_tz(row[c], tz)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-lineages", type=int, required=True)
    ap.add_argument("--tz", default="America/Chicago")
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    org = args.org
    src_map = {k: v.format(ORG=org) for k, v in SOURCE_MAP_TEMPLATE.items()}
    time_cols = ("event_at", "available_at", "submitted_at", "coverage_end",
                 "first_payment_at", "close_at", "closed_at", "observation_end")

    # 1. generate with the study generator (three-site structure), to a temp dir
    tmp = os.path.join("/tmp", f"org_scenario_{org}_{args.seed}")
    gen = DataPreparationPipeline(seed=args.seed, n_lineages=args.n_lineages)
    gen.write(tmp)

    out_data = os.path.join(tmp, "processed")
    os.makedirs(os.path.join(out_data, "_ground_truth"), exist_ok=True)

    # 2. remap org token, source system, record id prefix, timezone
    prefix_map = {"CPL-": f"{org}-", "TRI-": f"{org}-", "NDX-": f"{org}-"}
    org_tokens = {"CPL", "TRI", "NDX"}

    def remap_row(row: dict, fix_time: bool = True) -> dict:
        for k, v in list(row.items()):
            if v is None:
                continue
            if k == "org_token" and v in org_tokens:
                row[k] = org
            elif k == "source_system" and v in src_map:
                row[k] = src_map[v]
            elif isinstance(v, str) and v.startswith(tuple(prefix_map)):
                for old, new in prefix_map.items():
                    if v.startswith(old):
                        row[k] = new + v[len(old):]
                        break
        if fix_time:
            row = _fix_time_columns(row, args.tz, time_cols)
        return row

    for name in ("bills.csv", "events.csv", "allocations.csv", "observation_windows.csv"):
        src = os.path.join(tmp, name)
        dst = os.path.join(out_data, name)
        with open(src, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows = [remap_row(r) for r in rows]
        with open(dst, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"[gen_org_scenario] {name}: {len(rows)} rows -> {os.path.relpath(dst, ROOT)}")

    for name in ("true_lineages.csv", "true_outcomes.csv"):
        src = os.path.join(tmp, "_ground_truth", name)
        dst = os.path.join(out_data, "_ground_truth", name)
        with open(src, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows = [remap_row(r) for r in rows]
        with open(dst, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"[gen_org_scenario] _ground_truth/{name}: {len(rows)} rows")

    # 3. adjudicated reference pairs from same-bill version chains
    with open(os.path.join(out_data, "bills.csv"), encoding="utf-8") as f:
        bills = list(csv.DictReader(f))
    by_bill: dict[tuple, list[dict]] = {}
    for b in bills:
        by_bill.setdefault((b["org_token"], b["bill_id"]), []).append(b)
    pairs: list[dict] = []
    for _, members in sorted(by_bill.items()):
        ordered = sorted(members, key=lambda m: int(m["version_id"]) if m["version_id"].isdigit() else 0)
        for a, b in zip(ordered, ordered[1:]):
            pairs.append({
                "left_record_id": a["record_id"],
                "right_record_id": b["record_id"],
                "same_lineage": "true",
                "adjudication_status": "confirmed",
            })
    ref_path = os.path.join(out_data, "reference_labels.csv")
    with open(ref_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["left_record_id", "right_record_id",
                                          "same_lineage", "adjudication_status"])
        w.writeheader()
        w.writerows(pairs)
    print(f"[gen_org_scenario] reference_labels.csv: {len(pairs)} adjudicated pairs")

    # 4. data manifest for the organization scenario (single org, three
    #    internal source systems)
    import json as _json
    with open(os.path.join(out_data, "bills.csv"), encoding="utf-8") as f:
        n_bills = sum(1 for _ in f) - 1
    with open(os.path.join(out_data, "events.csv"), encoding="utf-8") as f:
        n_events = sum(1 for _ in f) - 1
    with open(os.path.join(out_data, "allocations.csv"), encoding="utf-8") as f:
        n_allocs = sum(1 for _ in f) - 1
    with open(os.path.join(out_data, "observation_windows.csv"), encoding="utf-8") as f:
        n_windows = sum(1 for _ in f) - 1
    manifest = {
        "manifest_version": "1.0",
        "data_mode": "EXTERNAL_VALIDATION",
        "org_token": org,
        "source_systems": [src_map[k] for k in ("CPL_BILLING", "NDX_BILLING", "TRI_BILLING")],
        "seed": args.seed,
        "n_lineages": args.n_lineages,
        "business_start": "2022-07-01",
        "as_of": "2023-11-15",
        "generator_version": "0.1.0",
        "orgs": {org: f"{org} — external validation site, single organization"},
        "identified_data": False,
        "adjudicated_labels_held_out": True,
        "tables": {
            "bills": {"rows": n_bills},
            "events": {"rows": n_events},
            "allocations": {"rows": n_allocs},
            "observation_windows": {"rows": n_windows},
        },
    }
    with open(os.path.join(out_data, "data_manifest.json"), "w", encoding="utf-8") as f:
        _json.dump(manifest, f, indent=2)
    print(f"[gen_org_scenario] data_manifest.json written for {org}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
