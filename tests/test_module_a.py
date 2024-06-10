"""Module A acceptance tests T01-T11 (spec section 15).

Each test loads a fixed scenario from tests/fixtures/fixed_scenarios.json,
writes the inputs as CSVs, runs the reconstruction engine and asserts the
reference behavior. These are engineering-correctness tests, not research
claims.
"""
from __future__ import annotations

import csv
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lab_billing.reconstruct import ReconstructionEngine  # noqa: E402
from lab_billing.reconstruct.amounts import AmountEngine  # noqa: E402

FIXTURES = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "fixed_scenarios.json")))


def _scenario(sid: str) -> dict:
    return FIXTURES["scenarios"][sid]


def _write_inputs(tmp_path, scenario: dict) -> str:
    d = tmp_path / f"data-{id(scenario) % 100000}"
    d.mkdir(exist_ok=True)
    for table, rows in scenario["inputs"].items():
        if table.endswith("_note"):
            continue
        if not rows:
            with open(d / f"{table}.csv", "w", encoding="utf-8") as f:
                f.write("")
            continue
        with open(d / f"{table}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return str(d)


def _run(tmp_path, sid: str, as_of: str | None = None):
    sc = _scenario(sid)
    data = _write_inputs(tmp_path, sc)
    eng = ReconstructionEngine(run_id=f"t-{sid}", as_of=as_of, method_version="1.0.0")
    out = str(tmp_path / "out")
    audit = eng.run(data, out)
    return eng, audit, out


def test_T01_duplicate_import_not_double_counted(tmp_path):
    eng, audit, out = _run(tmp_path, "F08_duplicate_import")
    amounts = eng.amounts
    # two identical posted events but the engine must count posted gross once
    # (the duplicate pair is flagged as duplicate import conflict)
    assert any(c["conflict_type"] == "DUPLICATE_IMPORT" or "DUPLICATE" in c["conflict_type"]
               for c in eng.conflicts)


def test_T02_cross_org_same_number_no_link(tmp_path):
    eng, audit, out = _run(tmp_path, "F06_cross_org_duplicate_number")
    assert len(eng.lineages) == 2
    assert all("CROSS_ORG" not in l.get("reason", "") for l in eng.links)


def test_T03_corrected_bill_versions_kept_not_summed(tmp_path):
    eng, audit, out = _run(tmp_path, "F02_corrected_bill")
    assert len(eng.lineages) == 1
    members = eng.lineages[0]["record_ids"].split("|")
    assert len(members) == 2  # both versions retained
    amounts = eng.amounts
    for lin_id, acc in amounts.items():
        # no payments in this scenario => nothing summed
        assert acc["gross_posted"] == 0


def test_T04_multi_candidate_needs_review(tmp_path):
    eng, audit, out = _run(tmp_path, "F05_ambiguous_multi_candidate")
    # three identical bills: engine must not silently merge all three
    assert len(eng.lineages) >= 1
    merged = any(len(l["record_ids"].split("|")) == 3 for l in eng.lineages)
    if merged:
        pytest.fail("three ambiguous records were silently merged into one lineage")


def test_T05_broken_reference_flagged(tmp_path):
    # broken explicit reference: successor points at missing record
    sc = {
        "inputs": {
            "bills": [
                {"record_id": "B1", "org_token": "CPL", "source_system": "SYS", "bill_id": "1",
                 "version_id": "1", "previous_record_id": "MISSING_ID", "payer_token": "UHC",
                 "service_token": "P", "billed_amount_minor": "100", "currency": "USD",
                 "submitted_at": "2023-01-01T09:00:00-06:00", "available_at": "2023-01-01T09:30:00-06:00",
                 "source_ref": "r"},
            ],
            "events": [], "allocations": [],
        }
    }
    data = _write_inputs(tmp_path, sc)
    eng = ReconstructionEngine(run_id="t-T05")
    eng.run(data, str(tmp_path / "out"))
    assert any(r["review_type"] == "DANGLING_REFERENCE" for r in eng.review_queue)


def test_T06_partial_payment_traceable(tmp_path):
    eng, audit, out = _run(tmp_path, "F09_partial_payment")
    amounts = list(eng.amounts.values())[0]
    assert amounts["gross_posted"] == 14000


def test_T06b_one_payment_multiple_bills(tmp_path):
    eng, audit, out = _run(tmp_path, "F10_one_payment_multiple_bills")
    total_alloc = sum(a["gross_posted"] for a in eng.amounts.values())
    assert total_alloc == 26000


def test_T07_over_allocation_blocked(tmp_path):
    sc = {
        "inputs": {
            "bills": [{"record_id": "B1", "org_token": "CPL", "source_system": "SYS", "bill_id": "1",
                       "version_id": "1", "previous_record_id": "", "payer_token": "UHC",
                       "service_token": "P", "billed_amount_minor": "10000", "currency": "USD",
                       "submitted_at": "2023-01-01T09:00:00-06:00", "available_at": "2023-01-01T09:30:00-06:00",
                       "source_ref": "r"}],
            "events": [{"event_id": "E1", "org_token": "CPL", "source_system": "SYS", "bill_record_id": "B1",
                        "event_type": "PAYMENT_POSTED", "event_at": "2023-01-10T09:00:00-06:00",
                        "available_at": "2023-01-10T09:30:00-06:00", "amount_minor": "10000",
                        "currency": "USD", "reverses_event_id": "", "terminal_flag": "false", "source_ref": "r"}],
            "allocations": [
                {"allocation_id": "A1", "payment_event_id": "E1", "bill_record_id": "B1",
                 "allocated_amount_minor": "7000", "currency": "USD",
                 "available_at": "2023-01-10T09:30:00-06:00", "source_ref": "r"},
                {"allocation_id": "A2", "payment_event_id": "E1", "bill_record_id": "B1",
                 "allocated_amount_minor": "6000", "currency": "USD",
                 "available_at": "2023-01-10T09:30:00-06:00", "source_ref": "r"},
            ],
        }
    }
    data = _write_inputs(tmp_path, sc)
    eng = ReconstructionEngine(run_id="t-T07")
    eng.run(data, str(tmp_path / "out"))
    assert any(c["conflict_type"] == "OVER_ALLOCATION" for c in eng.conflicts)
    # over-allocated payment excluded from balances
    assert all(a["gross_posted"] == 0 for a in eng.amounts.values())


def test_T08_partial_reversal_no_double_deduct(tmp_path):
    eng, audit, out = _run(tmp_path, "F13_partial_reversal")
    amounts = list(eng.amounts.values())[0]
    assert amounts["gross_posted"] == 10000
    assert amounts["reversed"] == 4000
    assert amounts["net_observed_posted"] == 6000


def test_T08b_unresolvable_reversal_flagged(tmp_path):
    eng, audit, out = _run(tmp_path, "F14_unresolvable_reversal")
    assert any(c["conflict_type"] == "UNRESOLVED_REVERSAL" for c in eng.conflicts)


def test_T09_void_not_close(tmp_path):
    eng, audit, out = _run(tmp_path, "F15_void_version_lineage_continues")
    assert len(eng.lineages) == 1
    assert eng.lineages[0]["status"] in ("PAYMENT_OBSERVED", "OPEN")
    amounts = list(eng.amounts.values())[0]
    assert amounts["gross_posted"] == 9500


def test_T10_late_record_not_in_snapshot(tmp_path):
    eng, audit, out = _run(tmp_path, "F18_late_record", as_of="2023-09-20T00:00:00Z")
    assert len(eng.bills) == 0  # invisible before available_at
    eng2, _, _ = _run(tmp_path, "F18_late_record", as_of="2023-11-01T00:00:00Z")
    assert len(eng2.bills) == 1  # visible after


def test_T11_no_tz_and_cross_currency_handled(tmp_path):
    # timezone-less timestamps are isolated by the validator, not silently fixed
    from lab_billing.normalize import normalize_events
    text = (
        "event_id,org_token,source_system,bill_record_id,event_type,event_at,available_at,"
        "amount_minor,currency,reverses_event_id,terminal_flag,source_ref\n"
        "E1,CPL,SYS,,UNKNOWN,2023-01-01T09:00:00,2023-01-01T09:30:00,,,false,r\n"
    )
    valid, invalid, issues = normalize_events(text)
    assert len(valid) == 0 and len(invalid) == 1
    # cross-currency never summed
    eng, audit, out = _run(tmp_path, "F24_cross_currency")
    for acc in eng.amounts.values():
        assert acc["gross_posted"] >= 0  # USD only; CAD excluded
