"""P06 validation: compare methods against hidden ground truth (spec 10, 13, 16).

Module A: precision/recall of accepted links against true lineage adjacency
(from _ground_truth/true_lineages.csv — never available to the linkers).
Module B: B0 vs B1 vs C1 ablations on the locked test set; refusal and
coverage analysis. All numbers trace back to a run's artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def load_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truth_adjacency_pairs(data_dir: str) -> set[tuple[str, str]]:
    """Reference pairs: same-lineage adjacent versions.

    Precedence:
    1. reference_labels.csv (adjudicated labels) when present — used for
       external validation datasets.
    2. _ground_truth/true_lineages.csv (held-out study labels) otherwise.
    In both cases explicit previous_record_id references are added, and
    same-bill-id version chains contribute adjacency pairs.
    """
    bills = load_csv(os.path.join(data_dir, "bills.csv"))
    pairs: set[tuple[str, str]] = set()

    # explicit references are always reference pairs
    for b in bills:
        prev = (b.get("previous_record_id") or "").strip()
        if prev:
            pairs.add((prev, b["record_id"]))

    # same-bill-id version chains
    by_bill: dict[tuple, list[dict]] = defaultdict(list)
    for b in bills:
        by_bill[(b["org_token"], b["bill_id"])].append(b)
    for _, members in by_bill.items():
        ordered = sorted(members, key=lambda m: int(m["version_id"]) if m["version_id"].isdigit() else 0)
        for a, b in zip(ordered, ordered[1:]):
            pairs.add((a["record_id"], b["record_id"]))

    labels = load_csv(os.path.join(data_dir, "reference_labels.csv"))
    if labels:
        # adjudicated same-lineage pairs from the validator's own staff
        pairs |= {(r["left_record_id"], r["right_record_id"]) for r in labels
                  if (r.get("same_lineage") or "").strip().lower() == "true"
                  and (r.get("adjudication_status") or "").strip().lower() == "confirmed"}
        return pairs

    true_lin = load_csv(os.path.join(data_dir, "_ground_truth", "true_lineages.csv"))
    if true_lin:
        lin_of = {r["record_id"]: r["true_lineage_id"] for r in true_lin}
        return {(a, b) for (a, b) in pairs
                if a in lin_of and b in lin_of and lin_of[a] == lin_of[b]}
    return pairs


def evaluate_module_a(data_dir: str, module_a_dir: str) -> dict:
    truth = truth_adjacency_pairs(data_dir)
    links = load_csv(os.path.join(module_a_dir, "links.csv"))
    pred = {(l["left_record_id"], l["right_record_id"]) for l in links}
    rq = load_csv(os.path.join(module_a_dir, "review_queue.csv"))
    tp = len(pred & truth)
    fp = len(pred - truth)
    fn = len(truth - pred)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(truth) if truth else 0.0
    return {
        "truth_pairs": len(truth),
        "predicted_pairs": len(pred),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "refusal_ratio": round(len(rq) / (len(rq) + len(pred)), 4) if (rq or pred) else 0.0,
        "note": "Truth pairs are same-lineage adjacent versions; multi-candidate "
                "ambiguities queued for review count as neither TP nor FP.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data_dir = os.path.join(args.run_dir, "data")
    a_dir = os.path.join(args.run_dir, "module_a")
    b_dir = os.path.join(args.run_dir, "module_b")

    report = {
        "validation_version": "1.0",
        "run_dir": args.run_dir,
        "module_a": evaluate_module_a(data_dir, a_dir),
        "module_b": {},
        "ablations": {},
        "limitations": {},
    }

    metrics = {}
    mp = os.path.join(b_dir, "forecast_metrics.json")
    if os.path.exists(mp):
        metrics = json.load(open(mp, encoding="utf-8"))
        report["module_b"] = {
            "snapshots": metrics.get("n_snapshots"),
            "test_snapshots": metrics.get("n_test_snapshots"),
            "outcomes": metrics.get("outcomes"),
            "models": {k: {kk: vv for kk, vv in v.items()
                           if kk in ("status", "snap_log_loss", "snap_brier",
                                     "n_abstain", "n_snapshots")}
                       for k, v in metrics.get("models", {}).items()},
        }
        m = metrics.get("models", {})
        b1 = m.get("B1_discrete_multinomial", {}).get("snap_log_loss")
        c1 = m.get("C1_quality_augmented", {}).get("snap_log_loss")
        b0 = m.get("B0_age_stage_baseline", {}).get("snap_log_loss")
        if b1 is not None and c1 is not None:
            report["ablations"]["quality_features"] = {
                "B1_snap_log_loss": b1,
                "C1_snap_log_loss": c1,
                "delta": round(c1 - b1, 4),
                "interpretation": ("quality features add no incremental value on the "
                                   "locked test set" if abs(c1 - b1) < 0.01
                                   else "quality features change performance"),
            }
        if b0 is not None and b1 is not None:
            report["ablations"]["candidate_vs_baseline"] = {
                "B0_snap_log_loss": b0,
                "B1_snap_log_loss": b1,
                "relative_improvement": round((b0 - b1) / b0, 4) if b0 else None,
            }

    report["limitations"] = {
        "study_scope": "All figures come from the study dataset of three participating sites. "
                     "No research claim transfers to real operations.",
        "censored_share": metrics.get("outcomes", {}).get("censored", 0),
        "close_class_rarity": metrics.get("outcomes", {}).get("close_no_payment", 0),
        "landmark_fixed": "landmark=7d and H=30d are study defaults pending "
                          "business confirmation (unknowns U03/U04).",
        "leakage_audit": "T10/T13/T14/T15 enforced: as-of truncation, forbidden "
                         "fields, lineage-grouped splits, train-only preprocessing.",
    }

    out_path = args.out or os.path.join(b_dir, "validation_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
