"""Forecast pipeline (module B orchestration).

snapshots -> interval rows -> temporal grouped split -> B0/B1/C1 fit on
train -> evaluation on locked test -> predictions + model card + feature
manifest. Same-lineage rows never span splits (T14).
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass

from .models import (
    B0AgeStageBaseline,
    DiscreteMultinomial,
    build_interval_rows,
    cumulative_curves,
    evaluate,
    evaluate_snapshots,
)
from .snapshot import Snapshot, SnapshotBuilder


@dataclass
class SplitResult:
    train_rows: list
    test_rows: list
    test_snaps: list


def temporal_grouped_split(rows: list, snaps: list[Snapshot],
                           ratios=(0.6, 0.2, 0.2)) -> SplitResult:
    """Group rows by lineage, sort lineages by first-submission time,
    split 60/20/20; test portion is locked."""
    from collections import defaultdict

    lin_first: dict[str, float] = {}
    for s in snaps:
        t0 = s.t.timestamp() - s.features.get("age_days", 0) * 86400
        lin_first[s.lineage_id] = min(lin_first.get(s.lineage_id, float("inf")), t0)
    order = sorted(lin_first, key=lambda k: lin_first[k])
    n = len(order)
    i1 = int(n * ratios[0])
    i2 = int(n * (ratios[0] + ratios[1]))
    train_lins = set(order[:i1])
    test_lins = set(order[i2:])
    train_rows = [r for r in rows if r.lineage_id in train_lins]
    test_rows = [r for r in rows if r.lineage_id in test_lins]
    test_snaps = [s for s in snaps if s.lineage_id in test_lins]
    return SplitResult(train_rows, test_rows, test_snaps)


class ForecastPipeline:
    def __init__(self, run_id: str, horizon_days: int = 30,
                 landmark_days: int = 7, interval_days: int = 5,
                 method_version: str = "1.0.0"):
        self.run_id = run_id
        self.horizon_days = horizon_days
        self.landmark_days = landmark_days
        self.interval_days = interval_days
        self.method_version = method_version

    def run(self, module_a_dir: str, out_dir: str) -> dict:
        os.makedirs(out_dir, exist_ok=True)
        lineages = list(csv.DictReader(open(
            os.path.join(module_a_dir, "lineages.csv"), encoding="utf-8")))
        events = list(csv.DictReader(open(
            os.path.join(module_a_dir, "events_normalized.csv"), encoding="utf-8")))
        allocations = list(csv.DictReader(open(
            os.path.join(module_a_dir, "allocations_normalized.csv"), encoding="utf-8")))
        if not events:
            raise FileNotFoundError("events_normalized.csv missing in module A output")

        builder = SnapshotBuilder(
            landmark_days=self.landmark_days,
            horizon_days=self.horizon_days,
            interval_days=self.interval_days,
        )
        snaps = builder.build(lineages, events, allocations)
        rows = build_interval_rows(snaps, horizon_days=self.horizon_days,
                                   interval_days=self.interval_days)
        split = temporal_grouped_split(rows, snaps)

        report = {
            "run_id": self.run_id,
            "method_version": self.method_version,
            "n_snapshots": len(snaps),
            "n_interval_rows": len(rows),
            "n_train_rows": len(split.train_rows),
            "n_test_rows": len(split.test_rows),
            "n_test_snapshots": len(split.test_snaps),
            "outcomes": {},
            "models": {},
        }
        from collections import Counter
        report["outcomes"] = dict(Counter(s.outcome for s in snaps))

        # B0
        b0 = B0AgeStageBaseline()
        b0.fit(split.train_rows)
        b0_metrics = evaluate(split.test_rows, _B0Adapter(b0))
        b0_snap = evaluate_snapshots(split.test_snaps, _B0Adapter(b0),
                                     self.horizon_days, self.interval_days)
        report["models"]["B0_age_stage_baseline"] = {"status": "FITTED",
                                                     **b0_metrics, **b0_snap}

        # B1
        b1 = DiscreteMultinomial(use_quality=False)
        b1_status = b1.fit(split.train_rows)
        b1_metrics = evaluate(split.test_rows, b1) if b1.fitted else {}
        b1_snap = evaluate_snapshots(split.test_snaps, b1, self.horizon_days,
                                     self.interval_days) if b1.fitted else {}
        report["models"]["B1_discrete_multinomial"] = {"status": b1_status,
                                                       **b1_metrics, **b1_snap}

        # C1
        c1 = DiscreteMultinomial(use_quality=True)
        c1_status = c1.fit(split.train_rows)
        c1_metrics = evaluate(split.test_rows, c1) if c1.fitted else {}
        c1_snap = evaluate_snapshots(split.test_snaps, c1, self.horizon_days,
                                     self.interval_days) if c1.fitted else {}
        report["models"]["C1_quality_augmented"] = {"status": c1_status,
                                                    **c1_metrics, **c1_snap}

        # predictions for test snapshots (prefer C1, fall back to B1)
        pred_model = c1 if c1.fitted else (b1 if b1.fitted else None)
        predictions = self._write_predictions(split.test_snaps, pred_model, b1, out_dir)

        # model card + feature manifest
        self._write_model_card(out_dir, report)
        self._write_feature_manifest(out_dir, pred_model)

        with open(os.path.join(out_dir, "forecast_metrics.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report

    def _write_predictions(self, snaps, model, b1, out_dir) -> list[dict]:
        rows_out = []
        for s in snaps:
            if not s.label_known:
                continue
            feats = _snap_features(s)
            interval_probs = []
            abstain = False
            for iv in range(max(1, self.horizon_days // self.interval_days)):
                feats["interval"] = float(iv)
                if model is not None:
                    p = model.predict_interval(feats)
                else:
                    p = None
                if p is None:
                    abstain = True
                    break
                interval_probs.append(p)
            if abstain:
                rows_out.append({
                    "snapshot_id": s.snapshot_id, "lineage_id": s.lineage_id,
                    "t": s.t.isoformat(), "outcome": "ABSTAIN",
                    "P_payment_by_H": "", "P_close_no_payment_by_H": "",
                    "P_still_open_by_H": "", "reason": "INSUFFICIENT_DATA_OR_NO_MODEL",
                })
                continue
            curves = cumulative_curves(interval_probs)
            rows_out.append({
                "snapshot_id": s.snapshot_id, "lineage_id": s.lineage_id,
                "t": s.t.isoformat(), "outcome": s.outcome,
                "P_payment_by_H": f"{curves['F_payment'][-1]:.6f}",
                "P_close_no_payment_by_H": f"{curves['F_close'][-1]:.6f}",
                "P_still_open_by_H": f"{curves['S'][-1]:.6f}",
                "reason": "",
            })
        _write_csv(os.path.join(out_dir, "predictions.csv"), rows_out)
        return rows_out

    def _write_model_card(self, out_dir: str, report: dict) -> None:
        card = f"""# Model card — module B (v{self.method_version})

- run_id: {self.run_id}
- target: FIRST_OBSERVED_POSITIVE_ALLOCATION_OR_NO_PAYMENT_CLOSURE
- landmark: {self.landmark_days} days after first observable submission
- horizon H: {self.horizon_days} days; interval: 1 day
- data: de-identified participating-site records (site tokens CPL/TRI/NDX).

## Snapshots and labels
{json.dumps(report["outcomes"], indent=2)}

## Models
{json.dumps(report["models"], indent=2)}

## Interpretation
- Probabilities are model outputs conditioned on interval features; they
  are not guarantees and not a claim of final collection.
- ABSTAIN means the model declined to predict (insufficient data or no
  fitted model); no fabricated probabilities.
- Censored observations never contribute negative labels.
"""
        with open(os.path.join(out_dir, "model_card.md"), "w", encoding="utf-8") as f:
            f.write(card)

    def _write_feature_manifest(self, out_dir: str, model) -> None:
        manifest = {
            "feature_version": self.method_version,
            "features": model.feature_cols if model else [],
            "forbidden_fields": [
                "record_id", "true_lineage_id", "future event fields",
                "final payment amounts", "test labels", "hidden truth ids",
            ],
            "leakage_guards": [
                "features computed only from available_at <= t",
                "hidden ground truth directory excluded from inputs",
                "temporal grouped split keeps lineages within one split",
            ],
        }
        with open(os.path.join(out_dir, "feature_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


class _B0Adapter:
    """Makes B0's empirical table evaluate-able through predict_interval."""

    def __init__(self, b0: B0AgeStageBaseline):
        self.b0 = b0

    def predict_interval(self, features):
        return self.b0.predict_interval(features)


def _snap_features(s: Snapshot) -> dict:
    from .models import _featurize
    return _featurize(s, 0)


def _write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
