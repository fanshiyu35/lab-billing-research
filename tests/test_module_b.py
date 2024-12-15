"""Module B acceptance tests T12-T19 (spec section 15).

Leakage guards, censoring discipline, probability constraints, insufficient
data handling, unseen-payer behavior, and first-event-only labeling.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lab_billing.forecast.models import (  # noqa: E402
    B0AgeStageBaseline,
    DiscreteMultinomial,
    IntervalRow,
    build_interval_rows,
    cumulative_curves,
)
from lab_billing.forecast.snapshot import Snapshot, SnapshotBuilder  # noqa: E402
from lab_billing.forecast.pipeline import temporal_grouped_split  # noqa: E402


def _mk_snap(outcome, interval=None, label_known=None, age=20.0,
             payer="commercial", qp=0):
    if label_known is None:
        label_known = outcome in ("payment", "close_no_payment", "still_open")
    feats = {
        "age_days": age, "payer_category": payer, "billed_amount_minor": 10000,
        "n_versions": 1, "n_corrected": 0, "n_voids": 0, "n_payments_pre_t": 0,
        "n_unknown_pre_t": 0, "n_status_updates_pre_t": 0, "n_closes_pre_t": 0,
        "n_reopens_pre_t": 0, "quality_penalty": qp, "coverage_status": "complete",
    }
    import datetime as _dt
    return Snapshot(
        snapshot_id=f"s-{outcome}-{interval}", lineage_id=f"L-{outcome}-{interval}",
        org_token="CPL", t=_dt.datetime(2023, 6, 1, tzinfo=_dt.timezone.utc),
        max_input_available_at=_dt.datetime(2023, 6, 1, tzinfo=_dt.timezone.utc),
        features=feats, outcome=outcome, outcome_interval=interval,
        label_known=label_known,
    )


def test_T12_insufficient_observation_not_negative():
    """Censored snapshots never become payment/close negatives."""
    snaps = [_mk_snap("censored", label_known=False)]
    rows = build_interval_rows(snaps)
    assert rows == []  # censored contributes no rows at all


def test_T13_hidden_truth_and_label_fields_rejected():
    """Feature vectors never contain hidden truth ids, true lineage ids or
    test labels."""
    from lab_billing.forecast.models import _featurize
    s = _mk_snap("payment", 2)
    feats = _featurize(s, 0)
    forbidden = ("record_id", "true_lineage_id", "outcome", "label",
                 "final_payment", "hidden", "true_outcome")
    assert not any(k in feats for k in forbidden)


def test_T14_no_lineage_across_splits():
    snaps = []
    for i in range(100):
        snaps.append(_mk_snap("payment" if i % 2 == 0 else "still_open",
                              interval=3 if i % 2 == 0 else None,
                              age=10 + i * 0.1))
    rows = build_interval_rows(snaps)
    split = temporal_grouped_split(rows, snaps)
    train_lins = {r.lineage_id for r in split.train_rows}
    test_lins = {r.lineage_id for r in split.test_rows}
    assert train_lins & test_lins == set()


def test_T15_preprocessing_fit_only_on_train():
    """StandardScaler statistics come from training rows only."""
    train_rows = [IntervalRow(f"t{i}", f"L{i}", 0,
                              {"age_days": float(i), "interval": 0.0,
                               "payer_commercial": 1.0}, "none")
                  for i in range(30)]
    train_rows += [IntervalRow(f"e1", "E1", 2, {"age_days": 50.0, "interval": 2.0,
                                                "payer_commercial": 1.0}, "payment")] * 6
    train_rows += [IntervalRow(f"e2", "E2", 3, {"age_days": 60.0, "interval": 3.0,
                                                "payer_commercial": 1.0}, "close_no_payment")] * 6
    m = DiscreteMultinomial()
    status = m.fit(train_rows)
    assert status == "FITTED"
    # mean of age_days must reflect train distribution, not a global stat
    assert m.scaler.mean_[0] < 60.0


def test_T16_probabilities_sum_to_one_and_curves_correct():
    # per-interval probabilities sum to 1
    probs = [{"payment": 0.2, "close_no_payment": 0.1, "none": 0.7},
             {"payment": 0.3, "close_no_payment": 0.1, "none": 0.6}]
    curves = cumulative_curves(probs)
    # F_payment(1) = S0 * p1 = 1 * 0.2
    assert abs(curves["F_payment"][0] - 0.2) < 1e-9
    # F_payment(2) = 0.2 + 0.7*0.3 = 0.41
    assert abs(curves["F_payment"][1] - 0.41) < 1e-9
    # S(2) = 0.7*0.6 = 0.42
    assert abs(curves["S"][1] - 0.42) < 1e-9
    # F_payment + F_close + S == 1 at the end
    assert abs(curves["F_payment"][-1] + curves["F_close"][-1]
               + curves["S"][-1] - 1.0) < 1e-9
    # non-normalized input must raise
    with pytest.raises(ValueError):
        cumulative_curves([{"payment": 0.5, "close_no_payment": 0.5, "none": 0.2}])


def test_T17_insufficient_data_no_fabricated_model():
    rows = [IntervalRow(f"t{i}", f"L{i}", 0, {"age_days": 20.0, "interval": 0.0}, "none")
            for i in range(20)]
    rows += [IntervalRow("e1", "E1", 1, {"age_days": 20.0, "interval": 1.0}, "payment")]
    # close_no_payment class has 0 rows => INSUFFICIENT_DATA
    m = DiscreteMultinomial()
    assert m.fit(rows) == "INSUFFICIENT_DATA"
    assert not m.fitted


def test_T18_unseen_payer_b0_abstains():
    b0 = B0AgeStageBaseline()
    rows = []
    for i in range(20):
        rows.append(IntervalRow(f"t{i}", f"L{i}", 0,
                                {"age_days": 20.0, "interval": 0.0,
                                 "payer_category_key": "commercial"}, "none"))
    rows += [IntervalRow("e1", "E1", 1,
                         {"age_days": 20.0, "interval": 1.0,
                          "payer_category_key": "commercial"}, "payment")] * 6
    b0.fit(rows)
    # unseen payer cell => ABSTAIN (None), never a guess
    assert b0.predict_interval({"age_days": 20.0, "interval": 0.0,
                                "payer_category_key": "government"}) is None


def test_T19_first_event_only_after_reopen():
    """Labeling picks the FIRST observable outcome; later reopen/payment do
    not rewrite the first close event (v1 predicts first events only)."""
    # snapshot where a close is first observable in interval 1 and a payment
    # arrives in interval 4: label must be close_no_payment@1
    snaps = [_mk_snap("close_no_payment", interval=1)]
    rows = build_interval_rows(snaps)
    labels = [(r.interval, r.label) for r in rows]
    assert labels == [(0, "none"), (1, "close_no_payment")]
    # no rows generated after the event
    assert len(rows) == 2
