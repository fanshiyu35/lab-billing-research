"""Regression tests for reconstruction and forecasting edge cases (C-01 through C-10)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lab_billing.reconstruct.amounts import AmountEngine
from lab_billing.reconstruct.rules import generate_r3_candidates
from lab_billing.forecast.snapshot import SnapshotBuilder, _utc
from lab_billing.forecast.models import DiscreteMultinomial, cumulative_curves


def T(iso: str) -> str:
    return iso


# ---------------------------------------------------------------- fixtures
def make_lineages():
    return [
        {"lineage_id": "L1", "org_token": "CPL", "record_ids": "B1|B2",
         "payer_category": "commercial", "billed_amount_minor": 1200,
         "conflict_count": 0, "review_count": 0,
         "coverage_status": "complete", "coverage_end": "2023-12-31T00:00:00Z"},
        {"lineage_id": "L2", "org_token": "CPL", "record_ids": "B3",
         "payer_category": "government", "billed_amount_minor": 800,
         "conflict_count": 0, "review_count": 0,
         "coverage_status": "complete", "coverage_end": "2023-12-31T00:00:00Z"},
    ]


# ------------------------------------------------------------------ C-01
def test_c01_payment_attaches_via_allocations():
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "amount_minor": 500, "currency": "USD"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 500, "currency": "USD"},
    ]
    lin_of = {"B1": "L1", "B2": "L1", "B3": "L2"}
    out = eng.compute(events, allocs, lin_of)
    assert "L1" in out, "payment must attach to L1 via allocation"
    assert out["L1"].gross_posted == 500
    assert "UNLINKED" not in out


# ------------------------------------------------------------------ C-02
def test_c02_partial_allocation_remainder_unallocated():
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "amount_minor": 1000, "currency": "USD"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 600, "currency": "USD"},
    ]
    lin_of = {"B1": "L1", "B2": "L1"}
    out = eng.compute(events, allocs, lin_of)
    assert out["L1"].unallocated == 400


# ------------------------------------------------------------------ C-03
def test_c03_cumulative_reversal_cap():
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "amount_minor": 1000, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B2",
         "amount_minor": 700, "currency": "USD", "reverses_event_id": "P1"},
        {"event_id": "R2", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B2",
         "amount_minor": 700, "currency": "USD", "reverses_event_id": "P1"},
    ]
    lin_of = {"B1": "L1", "B2": "L1"}
    out = eng.compute(events, [], lin_of)
    assert out["L1"].reversed == 1000, "cumulative reversals must cap at posted"


# ------------------------------------------------------------------ C-04
def test_c04_payment_spanning_multiple_lineages():
    b = SnapshotBuilder()
    lineages = make_lineages()
    events = [
        {"event_id": "S1", "event_type": "SUBMITTED", "bill_record_id": "B1",
         "available_at": "2023-09-01T00:00:00Z", "amount_minor": None, "currency": ""},
        {"event_id": "S2", "event_type": "SUBMITTED", "bill_record_id": "B3",
         "available_at": "2023-09-01T00:00:00Z", "amount_minor": None, "currency": ""},
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "available_at": "2023-09-20T00:00:00Z", "amount_minor": 900, "currency": "USD"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 500, "currency": "USD",
         "available_at": "2023-09-20T00:00:00Z"},
        {"allocation_id": "A2", "payment_event_id": "P1", "bill_record_id": "B3",
         "allocated_amount_minor": 400, "currency": "USD",
         "available_at": "2023-09-20T00:00:00Z"},
    ]
    snaps = b.build(lineages, events, allocs)
    lids = {s.lineage_id for s in snaps}
    assert lids == {"L1", "L2"}, "payment visible on both lineages"


# ------------------------------------------------------------------ C-05
def test_c05_payment_observable_time_uses_allocation_available_at():
    b = SnapshotBuilder()
    lineages = make_lineages()
    sub_t = "2023-09-01T00:00:00Z"
    pay_avail = "2023-09-10T00:00:00Z"   # early
    alloc_avail = "2023-09-25T00:00:00Z"  # later
    events = [
        {"event_id": "S1", "event_type": "SUBMITTED", "bill_record_id": "B1",
         "available_at": sub_t, "amount_minor": None, "currency": ""},
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "available_at": pay_avail, "amount_minor": 900, "currency": "USD"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 900, "currency": "USD", "available_at": alloc_avail},
    ]
    snaps = b.build(lineages, events, allocs)
    # landmark t = 2023-09-08; payment effective at 2023-09-25 => after t
    s = snaps[0]
    assert s.outcome == "payment", s
    # interval must be computed from the effective time (>= 3 intervals out)
    t = datetime.fromisoformat("2023-09-08T00:00:00+00:00")
    when = datetime.fromisoformat("2023-09-25T00:00:00+00:00")
    iv = int((when - t).total_seconds() // (5 * 86400))
    assert s.outcome_interval == iv


# ------------------------------------------------------------------ C-06
def test_c06_no_seventh_interval_at_horizon_boundary():
    b = SnapshotBuilder()
    lineages = make_lineages()
    sub_t = "2023-09-01T00:00:00Z"
    # payment exactly at t + 30 days
    events = [
        {"event_id": "S1", "event_type": "SUBMITTED", "bill_record_id": "B1",
         "available_at": sub_t, "amount_minor": None, "currency": ""},
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "available_at": "2023-10-08T00:00:00Z", "amount_minor": 900, "currency": "USD"},
    ]
    snaps = b.build(lineages, events, [])
    # t = 2023-09-08; H_end = 2023-10-08 (exclusive)
    assert snaps[0].outcome != "payment", "event at exact horizon endpoint excluded"
    assert snaps[0].outcome in ("still_open", "censored")


# ------------------------------------------------------------------ C-07
def test_c07_outcome_before_landmark_excluded():
    b = SnapshotBuilder()
    lineages = make_lineages()
    sub_t = "2023-09-01T00:00:00Z"
    events = [
        {"event_id": "S1", "event_type": "SUBMITTED", "bill_record_id": "B1",
         "available_at": sub_t, "amount_minor": None, "currency": ""},
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "available_at": "2023-09-03T00:00:00Z", "amount_minor": 900, "currency": "USD"},
    ]
    snaps = b.build(lineages, events, [])
    assert snaps == [], "lineage with pre-landmark outcome is not a prediction target"


# ------------------------------------------------------------------ C-08
def test_c08_simultaneous_payment_and_close_deterministic():
    b = SnapshotBuilder()
    lineages = make_lineages()
    sub_t = "2023-09-01T00:00:00Z"
    base = [
        {"event_id": "S1", "event_type": "SUBMITTED", "bill_record_id": "B1",
         "available_at": sub_t, "amount_minor": None, "currency": ""},
    ]
    same_time = "2023-09-20T00:00:00Z"
    tail = [
        {"event_id": "C1", "event_type": "CLOSED_NO_PAYMENT", "bill_record_id": "B2",
         "available_at": same_time, "amount_minor": None, "currency": ""},
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "available_at": same_time, "amount_minor": 900, "currency": "USD"},
    ]
    r1 = b.build(lineages, base + tail, [])
    r2 = b.build(lineages, base + list(reversed(tail)), [])
    assert r1[0].outcome == r2[0].outcome == "payment"


# ------------------------------------------------------------------ C-09
def test_c09_negative_probability_rejected():
    with pytest.raises(ValueError):
        cumulative_curves([{"payment": 1.1, "close_no_payment": -0.1, "none": 0.0}])


# ------------------------------------------------------------------ C-10
def test_c10_r3_does_not_cross_source_systems():
    bills = [
        {"record_id": "b1", "org_token": "CPL", "source_system": "SYS_A",
         "payer_token": "AET", "service_token": "SV1",
         "billed_amount_minor": 100, "submitted_at": datetime(2023, 1, 1, tzinfo=timezone.utc)},
        {"record_id": "b2", "org_token": "CPL", "source_system": "SYS_B",
         "payer_token": "AET", "service_token": "SV1",
         "billed_amount_minor": 100, "submitted_at": datetime(2023, 1, 2, tzinfo=timezone.utc)},
    ]
    cands = generate_r3_candidates(bills)
    assert cands == [], "R3 candidates must not cross source systems"


# ------------------------------------------------------------------ C-11
def test_c11_reversal_cap_is_per_payment_not_per_lineage():
    """Two fully-reversed payments on the same lineage must both reverse."""
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "amount_minor": 100, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B2",
         "amount_minor": 100, "currency": "USD", "reverses_event_id": "P1"},
        {"event_id": "P2", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "amount_minor": 100, "currency": "USD"},
        {"event_id": "R2", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B2",
         "amount_minor": 100, "currency": "USD", "reverses_event_id": "P2"},
    ]
    lin_of = {"B2": "L1"}
    out = eng.compute(events, [], lin_of)
    assert out["L1"].gross_posted == 200
    assert out["L1"].reversed == 200, "second payment's reversal must not be capped by the first"
    assert out["L1"].net_observed_posted == 0


# ------------------------------------------------------------------ C-12
def test_c12_payment_split_across_lineages_attributed_per_allocation():
    """A payment spanning two lineages must split gross, unallocated and
    reversals in proportion to its allocations, not dump everything on the
    first lineage found."""
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "amount_minor": 1000, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "",
         "amount_minor": 400, "currency": "USD", "reverses_event_id": "P1"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 600, "currency": "USD"},
        {"allocation_id": "A2", "payment_event_id": "P1", "bill_record_id": "B3",
         "allocated_amount_minor": 200, "currency": "USD"},
    ]
    lin_of = {"B2": "L1", "B3": "L2"}
    out = eng.compute(events, allocs, lin_of)
    # gross: L1 600 + unalloc 200 (single-lineage remainder attaches to L1's
    # allocated lineage here is NOT single — allocations span L1 and L2, so
    # the unallocated 200 belongs to UNLINKED)
    assert out["L1"].gross_posted == 600, out["L1"]
    assert out["L2"].gross_posted == 200, out["L2"]
    assert out["UNLINKED"].gross_posted == 200, out.get("UNLINKED")
    assert out["UNLINKED"].unallocated == 200
    # reversal 400 split across the three attribution parts (600:200:200)
    assert out["L1"].reversed == 240, out["L1"]
    assert out["L2"].reversed == 80, out["L2"]
    assert out["UNLINKED"].reversed == 80, out.get("UNLINKED")
    # net check
    assert out["L1"].net_observed_posted == 600 - 240
    assert out["L2"].net_observed_posted == 200 - 80


def test_p302_two_payments_same_lineage_each_fully_reversed():
    """Pro P3-02 counterexample: two equal payments on one lineage, each fully
    reversed. The first payment's reversal must not consume the second
    payment's reversal cap."""
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "B1",
         "amount_minor": 1000, "currency": "USD"},
        {"event_id": "P2", "event_type": "PAYMENT_POSTED", "bill_record_id": "B2",
         "amount_minor": 1000, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B1",
         "amount_minor": 1000, "currency": "USD", "reverses_event_id": "P1"},
        {"event_id": "R2", "event_type": "PAYMENT_REVERSED", "bill_record_id": "B2",
         "amount_minor": 1000, "currency": "USD", "reverses_event_id": "P2"},
    ]
    lin_of = {"B1": "L1", "B2": "L1"}
    out = eng.compute(events, [], lin_of)
    acc = out["L1"]
    assert acc.gross_posted == 2000, acc
    assert acc.reversed == 2000, f"both payments must be fully reversed, got {acc.reversed}"
    assert acc.net_observed_posted == 0, acc


# ------------------------------------------------------------------ C-13
def test_c13_lineage_level_reversal_cap_pro_counterexample():
    """Pro review finding 13: one 100-cent payment split 50/50 across two
    lineages, reversed in two steps (1c then 99c). The cumulative reversal of
    a lineage may not exceed its own gross attribution."""
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "amount_minor": 100, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "",
         "amount_minor": 1, "currency": "USD", "reverses_event_id": "P1"},
        {"event_id": "R2", "event_type": "PAYMENT_REVERSED", "bill_record_id": "",
         "amount_minor": 99, "currency": "USD", "reverses_event_id": "P1"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B1",
         "allocated_amount_minor": 50, "currency": "USD"},
        {"allocation_id": "A2", "payment_event_id": "P1", "bill_record_id": "B2",
         "allocated_amount_minor": 50, "currency": "USD"},
    ]
    lin_of = {"B1": "LA", "B2": "LB"}
    out = eng.compute(events, allocs, lin_of)
    assert out["LA"].gross_posted == 50, out["LA"]
    assert out["LB"].gross_posted == 50, out["LB"]
    assert out["LA"].reversed == 50, f"LA must be capped at its 50 gross, got {out['LA'].reversed}"
    assert out["LB"].reversed == 50, f"LB must be capped at its 50 gross, got {out['LB'].reversed}"
    assert out["LA"].net_observed_posted == 0, out["LA"]
    assert out["LB"].net_observed_posted == 0, out["LB"]
    assert out["LA"].reversed + out["LB"].reversed == 100, "payment fully reversed"


# ------------------------------------------------------------------ C-14
def test_c14_repeated_lineage_parts_aggregate_before_split():
    """Pro finding N4: a payment whose allocations map to the SAME lineage
    (e.g. 40 allocated + 60 unallocated remainder, both to lineage A) must
    not produce duplicated shares that double-count on reversal."""
    eng = AmountEngine("t")
    events = [
        {"event_id": "P1", "event_type": "PAYMENT_POSTED", "bill_record_id": "",
         "amount_minor": 100, "currency": "USD"},
        {"event_id": "R1", "event_type": "PAYMENT_REVERSED", "bill_record_id": "",
         "amount_minor": 100, "currency": "USD", "reverses_event_id": "P1"},
    ]
    allocs = [
        {"allocation_id": "A1", "payment_event_id": "P1", "bill_record_id": "B1",
         "allocated_amount_minor": 40, "currency": "USD"},
    ]
    lin_of = {"B1": "LA"}
    out = eng.compute(events, allocs, lin_of)
    acc = out["LA"]
    assert acc.gross_posted == 100, acc
    assert acc.reversed == 100, f"full reversal must fully reverse, got {acc.reversed}"
    assert acc.net_observed_posted == 0, acc


# ------------------------------------------------------------------ C-15
def test_c15_alloc_time_compared_chronologically_not_lexicographically():
    """Pro finding N5: two allocation timestamps with different UTC offsets
    must be ordered by actual instant, not by raw string comparison."""
    a = "2023-11-05T01:30:00-04:00"   # 05:30 UTC
    b = "2023-11-05T01:15:00-05:00"   # 06:15 UTC
    assert _utc(a) < _utc(b), "string order would wrongly pick b; chronological order must pick a"
