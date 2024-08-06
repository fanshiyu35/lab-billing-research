"""Synthetic demo data generator (spec section 09).

Deterministic (seed 42). Generates observable inputs plus hidden ground truth
(true lineage ids and future payment dates). The hidden truth is written to a
separate directory and must never enter training or inference features.

Realism requirements: amounts follow plausible laboratory pricing, timestamps
follow business-weekday and local-timezone rhythms, late-arriving records and
dirty-data cases (duplicate imports, cross-org duplicate numbers, missing
references, timezone-less timestamps, illegal amounts) are injected on
purpose so the reconstruction task is non-trivial.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

ORG_TZ = {
    "CPL": "America/Chicago",
    "TRI": "America/Denver",
    "NDX": "America/New_York",
}

ORG_WEIGHT = {"CPL": 0.40, "TRI": 0.35, "NDX": 0.25}

# payer mix: token -> (share, typical delay days mean)
PAYER_MIX = [
    ("UHC", 0.20, 21.0), ("AET", 0.18, 22.0), ("MCR", 0.22, 14.0),
    ("MCD", 0.10, 35.0), ("SELF", 0.08, 9.0), ("HUM", 0.07, 24.0),
    ("BCB", 0.06, 19.0), ("CIG", 0.04, 20.0), ("", 0.05, 26.0),
]

# service mix: (name, share, price_mean, price_sigma) prices in USD minor units
SERVICE_MIX = [
    ("BASIC_PANEL", 0.38, 6800, 0.55),
    ("CHEM_PROFILE", 0.22, 12500, 0.45),
    ("MOLECULAR", 0.15, 68000, 0.75),
    ("ANATOMIC_PATH", 0.10, 24500, 0.60),
    ("TOXICOLOGY", 0.08, 42000, 0.65),
    ("MICROBIOLOGY", 0.07, 18900, 0.50),
]


@dataclass
class Chain:
    org: str
    lineage_id: str
    payer: str
    service: str
    submitted_at: datetime  # local tz
    billed_minor: int
    record_ids: list  # version record ids in order


def _fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class SyntheticGenerator:
    def __init__(self, seed: int = 42, n_lineages: int = 1000,
                 business_start: str = "2022-07-01", as_of: str = "2023-11-15"):
        self.rng = np.random.default_rng(seed)
        self.n_lineages = n_lineages
        self.business_start = datetime.fromisoformat(business_start).replace(tzinfo=ZoneInfo("UTC"))
        self.as_of = datetime.fromisoformat(as_of).replace(tzinfo=ZoneInfo("UTC"))
        self.bills: list[dict] = []
        self.events: list[dict] = []
        self.allocations: list[dict] = []
        self.true_lineages: list[dict] = []
        self.true_outcomes: list[dict] = []
        self._bill_counter = {org: 0 for org in ORG_TZ}
        self._record_counter = 0
        self._event_counter = 0
        self._alloc_counter = 0
        self._lin_counter = 0

    # ---------------------------------------------------------------- helpers
    def _next_lineage_id(self) -> str:
        self._lin_counter += 1
        return f"L{self._lin_counter:05d}"

    def _next_bill_id(self, org: str) -> str:
        """Native bill numbers per org; numeric cores overlap across orgs on
        purpose so cross-org duplicate numbers occur naturally."""
        self._bill_counter[org] += 1
        n = self._bill_counter[org]
        if org == "CPL":
            return f"{2022 + (n % 2):d}-{4000000 + n:07d}"
        if org == "TRI":
            return f"{2000000 + n:07d}"
        return f"{8000000 + n:08d}"

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"EV{self._event_counter:06d}"

    def _next_alloc_id(self) -> str:
        self._alloc_counter += 1
        return f"AL{self._alloc_counter:06d}"

    def _src_ref(self, org: str, kind: str) -> str:
        return f"{org}/demo/{kind}/{self._event_counter or self._lin_counter:05d}"

    def _workday_seconds(self, org: str, d: datetime) -> datetime:
        """Shift to a business hour on a weekday, local time."""
        local = d.astimezone(ZoneInfo(ORG_TZ[org]))
        while local.weekday() >= 5:  # Sat/Sun
            local += timedelta(days=1)
        h = int(self.rng.integers(8, 17))
        m = int(self.rng.integers(0, 60))
        local = local.replace(hour=h, minute=m, second=0, microsecond=0)
        return local

    def _random_time(self, org: str) -> datetime:
        """Uniform business time in the window, local working hours."""
        span = (self.as_of - timedelta(days=45)) - self.business_start
        secs = int(span.total_seconds())
        t = self.business_start + timedelta(seconds=int(self.rng.integers(0, secs)))
        return self._workday_seconds(org, t)

    def _late_arrival(self, dt: datetime) -> datetime:
        """available_at is when the system learned of the event. In real
        billing systems a large share of events are recorded same-day; the
        rest lag by days, with occasional very late arrivals."""
        if self.rng.random() < 0.45:  # same-day entry, hour-level lag
            lag = timedelta(hours=float(self.rng.uniform(0.1, 8.0)))
            return dt + lag
        lag_days = float(self.rng.lognormal(mean=1.1, sigma=0.9))
        lag_days = min(lag_days, 21.0)
        if self.rng.random() < 0.02:  # occasional very late arrivals
            lag_days = float(self.rng.uniform(30, 90))
        return dt + timedelta(days=lag_days)

    def _sample_payer(self) -> str:
        """Payer weighted by share of mix."""
        tokens = [p[0] for p in PAYER_MIX]
        shares = [p[1] for p in PAYER_MIX]
        return tokens[int(self.rng.choice(len(tokens), p=shares))]

    def _sample_service(self):
        """Service weighted by share of mix."""
        names = [s[0] for s in SERVICE_MIX]
        shares = [s[1] for s in SERVICE_MIX]
        idx = int(self.rng.choice(len(names), p=shares))
        return SERVICE_MIX[idx]

    def _payer_delay_days(self, payer: str) -> float:
        for tok, _share, mean in PAYER_MIX:
            if tok == payer:
                return float(self.rng.lognormal(mean=np.log(mean), sigma=0.65))
        return float(self.rng.lognormal(mean=np.log(20.0), sigma=0.65))

    def _emit_bill(self, chain: Chain, version: int, prev_record_id: str,
                   amount_minor: int, submitted_local: datetime,
                   bill_id: str | None = None) -> tuple[str, str]:
        """Return (record_id, bill_id) so corrections can reuse the bill_id."""
        self._record_counter += 1
        record_id = f"{chain.org}-R{self._record_counter:05d}"
        bid = bill_id if bill_id else self._next_bill_id(chain.org)
        available = self._late_arrival(submitted_local)
        self.bills.append({
            "record_id": record_id,
            "org_token": chain.org,
            "source_system": f"{chain.org}_BILLING",
            "bill_id": bid,
            "version_id": str(version),
            "previous_record_id": prev_record_id,
            "payer_token": chain.payer,
            "service_token": chain.service,
            "billed_amount_minor": int(amount_minor),
            "currency": "USD",
            "submitted_at": _fmt(submitted_local),
            "available_at": _fmt(available),
            "source_ref": self._src_ref(chain.org, "bills"),
        })
        return record_id, bid

    def _next_bill_id_num(self, org: str) -> int:
        return self._bill_counter[org] + 1

    def _emit_event(self, chain: Chain, event_type: str, at_local: datetime,
                    bill_record_id: str = "", amount_minor: int | None = None,
                    reverses_event_id: str = "", terminal: bool = False,
                    lag: bool = True, currency: str = "USD") -> str:
        eid = self._next_event_id()
        available = self._late_arrival(at_local) if lag else at_local
        ev = {
            "event_id": eid,
            "org_token": chain.org,
            "source_system": f"{chain.org}_BILLING",
            "bill_record_id": bill_record_id,
            "event_type": event_type,
            "event_at": _fmt(at_local),
            "available_at": _fmt(available),
            "amount_minor": "" if amount_minor is None else str(int(amount_minor)),
            "currency": currency if amount_minor is not None else "",
            "reverses_event_id": reverses_event_id,
            "terminal_flag": "true" if terminal else "false",
            "source_ref": self._src_ref(chain.org, "events"),
        }
        self.events.append(ev)
        return eid

    def _emit_allocation(self, payment_event_id: str, bill_record_id: str,
                         amount_minor: int, at_local: datetime, org: str) -> None:
        aid = self._next_alloc_id()
        self.allocations.append({
            "allocation_id": aid,
            "payment_event_id": payment_event_id,
            "bill_record_id": bill_record_id,
            "allocated_amount_minor": str(int(amount_minor)),
            "currency": "USD",
            "available_at": _fmt(self._late_arrival(at_local)),
            "source_ref": self._src_ref(org, "allocations"),
        })

    # ---------------------------------------------------------------- lineage lifecycle
    def _simulate_chain(self, org: str) -> None:
        rng = self.rng
        lid = self._next_lineage_id()
        payer = self._sample_payer()
        svc, _share, p_mean, p_sigma = self._sample_service()
        amount_minor = int(rng.lognormal(mean=np.log(p_mean), sigma=p_sigma))
        amount_minor = max(amount_minor, 2500)  # floor ~ $25

        submitted = self._random_time(org)
        chain = Chain(org=org, lineage_id=lid, payer=payer, service=svc,
                      submitted_at=submitted, billed_minor=amount_minor,
                      record_ids=[])

        # v1
        rid_v1, bid_v1 = self._emit_bill(chain, 1, "", amount_minor, submitted)
        chain.record_ids.append(rid_v1)
        self._emit_event(chain, "SUBMITTED", submitted, bill_record_id=rid_v1,
                         amount_minor=amount_minor)

        # correction branch (~10%)
        if rng.random() < 0.10:
            v2_amount = int(amount_minor * rng.uniform(0.85, 1.30))
            v2_time = submitted + timedelta(days=int(rng.integers(1, 12)))
            v2_time = self._workday_seconds(org, v2_time)
            if v2_time > self.as_of:
                v2_time = submitted
            # ~30% of corrections miss the native predecessor reference
            prev = rid_v1 if rng.random() >= 0.30 else ""
            rid_v2, _ = self._emit_bill(chain, 2, prev, v2_amount, v2_time,
                                        bill_id=bid_v1)
            chain.record_ids.append(rid_v2)
            self._emit_event(chain, "CORRECTED", v2_time, bill_record_id=rid_v2,
                             amount_minor=v2_amount)
            if rng.random() < 0.35:
                self._emit_event(chain, "VOID_VERSION", v2_time,
                                 bill_record_id=rid_v1, amount_minor=amount_minor)
            current_rid = rid_v2
            current_amount = v2_amount
        else:
            current_rid = rid_v1
            current_amount = amount_minor

        # outcome branch
        u = rng.random()
        if u < 0.06:  # closed no payment
            if payer in ("SELF", ""):
                close_days = int(rng.uniform(20, 55))  # quick self-pay write-offs
            else:
                close_days = int(rng.uniform(30, 120))
            close_time = submitted + timedelta(days=close_days)
            close_time = self._workday_seconds(org, close_time)
            self._emit_event(chain, "CLOSED_NO_PAYMENT", close_time,
                             bill_record_id=current_rid, terminal=True)
            self.true_outcomes.append({"true_lineage_id": lid, "outcome": "CLOSED_NO_PAYMENT",
                                       "close_at": _fmt(close_time)})
        elif u < 0.16:  # still open at as_of (recent submissions)
            self.true_outcomes.append({"true_lineage_id": lid, "outcome": "STILL_OPEN",
                                       "first_payment_at": "", "close_at": ""})
        else:  # payment path
            delay = self._payer_delay_days(payer)
            pay_time = submitted + timedelta(days=delay)
            pay_time = self._workday_seconds(org, pay_time)
            observed = pay_time <= self.as_of
            if not observed:
                self.true_outcomes.append({"true_lineage_id": lid, "outcome": "STILL_OPEN",
                                           "first_payment_at": _fmt(pay_time),
                                           "close_at": ""})
                return
            pay_event_id = self._emit_event(chain, "PAYMENT_POSTED", pay_time,
                                            bill_record_id="", amount_minor=current_amount)
            # allocation pattern: full / partial / multi-bill / unallocated
            pattern = rng.random()
            if pattern < 0.60:  # full allocation
                self._emit_allocation(pay_event_id, current_rid, current_amount, pay_time, org)
            elif pattern < 0.88:  # partial payment
                paid = int(current_amount * rng.uniform(0.55, 0.97))
                self._emit_allocation(pay_event_id, current_rid, paid, pay_time, org)
            elif pattern < 0.96:  # one payment, multiple bills (create a sibling bill)
                paid1 = int(current_amount * rng.uniform(0.45, 0.70))
                sibling_amount = int(rng.lognormal(mean=np.log(12000), sigma=0.5))
                sib_time = self._workday_seconds(org, submitted - timedelta(days=int(rng.integers(0, 6))))
                if sib_time < self.business_start:
                    sib_time = submitted
                sib_rid, _ = self._emit_bill(Chain(org, lid + "-S", payer, svc, sib_time,
                                                  sibling_amount, []), 1, "", sibling_amount, sib_time)
                self._emit_event(Chain(org, lid + "-S", payer, svc, sib_time, sibling_amount, []),
                                 "SUBMITTED", sib_time, bill_record_id=sib_rid,
                                 amount_minor=sibling_amount)
                self.true_lineages.append({"record_id": sib_rid, "true_lineage_id": lid})
                self._emit_allocation(pay_event_id, current_rid, paid1, pay_time, org)
                self._emit_allocation(pay_event_id, sib_rid,
                                      current_amount - paid1, pay_time, org)
            else:  # unallocated payment (2%)
                pass
            # reversal branch (~2.5% of paid)
            if rng.random() < 0.025:
                rev_amount = current_amount if rng.random() < 0.5 else int(current_amount * rng.uniform(0.2, 0.8))
                rev_time = self._workday_seconds(org, pay_time + timedelta(days=int(rng.integers(2, 15))))
                rev_ref = pay_event_id if rng.random() >= 0.15 else ""  # 15% unresolvable
                self._emit_event(chain, "PAYMENT_REVERSED", rev_time,
                                 bill_record_id=current_rid, amount_minor=rev_amount,
                                 reverses_event_id=rev_ref)
            self.true_outcomes.append({"true_lineage_id": lid, "outcome": "PAYMENT_POSTED",
                                       "first_payment_at": _fmt(pay_time), "close_at": ""})

        for rid in chain.record_ids:
            self.true_lineages.append({"record_id": rid, "true_lineage_id": lid})

    # ---------------------------------------------------------------- dirty injection
    def _inject_dirty(self) -> None:
        rng = self.rng
        n_ev = len(self.events)
        # duplicate import: copy a few event rows with new event ids
        dup_idx = rng.choice(n_ev, size=max(1, n_ev // 100), replace=False)
        for i in dup_idx:
            dup = dict(self.events[i])
            dup["event_id"] = self._next_event_id()
            dup["source_ref"] = dup["source_ref"] + "-DUP"
            self.events.append(dup)
        # timezone-less timestamps (~0.4%): strip offset entirely (invalid by contract)
        for ev in self.events:
            if rng.random() < 0.004:
                ev["event_at"] = re.sub(r"[+-]\d{2}:\d{2}$", "", ev["event_at"])
                ev["available_at"] = re.sub(r"[+-]\d{2}:\d{2}$", "", ev["available_at"])
        # illegal amount in a few bill rows (~0.3%)
        for b in self.bills:
            if rng.random() < 0.003:
                b["billed_amount_minor"] = "-1"
        # odd currency in a couple of events (~0.2%)
        for ev in self.events:
            if rng.random() < 0.002:
                ev["currency"] = "EUR"
        # cross-org duplicate bill numbers: force a handful of same-number collisions
        orgs = list(ORG_TZ)
        for _ in range(5):
            if len(self.bills) > 20:
                i, j = rng.choice(len(self.bills), size=2, replace=False)
                if self.bills[i]["org_token"] != self.bills[j]["org_token"]:
                    self.bills[j]["bill_id"] = self.bills[i]["bill_id"]
                    self.bills[j]["source_ref"] += "-XORG"
        # unresolvable reversal already injected in lifecycle (15%)
        # status unknown events (~0.5%)
        for _ in range(max(1, len(self.events) // 200)):
            org = orgs[int(rng.integers(0, 3))]
            t = self._random_time(org)
            self._emit_event(Chain(org, self._next_lineage_id(), "", "MISC", t, 0, []),
                             "UNKNOWN", t, bill_record_id="", amount_minor=None)

    # ---------------------------------------------------------------- main
    def generate(self) -> dict:
        for org in ORG_TZ:
            n = int(self.n_lineages * ORG_WEIGHT[org])
            for _ in range(n):
                self._simulate_chain(org)
        self._inject_dirty()
        windows = []
        wno = 0
        for org in ORG_TZ:
            tz = ZoneInfo(ORG_TZ[org])
            start = self.business_start.astimezone(tz)
            end = self.as_of.astimezone(tz)
            wno += 1
            windows.append({
                "window_id": f"W{wno:03d}",
                "org_token": org,
                "source_system": f"{org}_BILLING",
                "coverage_start": _fmt(start),
                "coverage_end": _fmt(end),
                "extracted_at": _fmt(self.as_of.astimezone(tz)),
                "coverage_status": "complete",
                "basis_ref": f"{org}/demo/coverage/primary",
            })
            wno += 1
            gap_start = start + timedelta(days=120)
            gap_end = gap_start + timedelta(days=9)
            windows.append({
                "window_id": f"W{wno:03d}",
                "org_token": org,
                "source_system": f"{org}_BILLING_LEGACY",
                "coverage_start": _fmt(gap_start),
                "coverage_end": _fmt(gap_end),
                "extracted_at": _fmt(self.as_of.astimezone(tz)),
                "coverage_status": "partial",
                "basis_ref": f"{org}/demo/coverage/legacy-gap",
            })
        return {
            "bills": self.bills,
            "events": self.events,
            "allocations": self.allocations,
            "observation_windows": windows,
            "true_lineages": self.true_lineages,
            "true_outcomes": self.true_outcomes,
        }

    def write(self, out_dir: str) -> None:
        import csv

        tables = self.generate()
        os.makedirs(out_dir, exist_ok=True)
        gt_dir = os.path.join(out_dir, "_ground_truth")
        os.makedirs(gt_dir, exist_ok=True)
        for name, rows in tables.items():
            if name in ("true_lineages", "true_outcomes"):
                path = os.path.join(gt_dir, f"{name}.csv")
            else:
                path = os.path.join(out_dir, f"{name}.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
                writer.writeheader()
                writer.writerows(rows)
        table_counts = {k: len(v) for k, v in tables.items()}
        manifest = {
            "manifest_version": "1.0",
            "generated_at": "2023-11-15",
            "data_mode": "DEMO",
            "seed": 42,
            "n_lineages": self.n_lineages,
            "business_start": self.business_start.isoformat(),
            "as_of": self.as_of.isoformat(),
            "generator_version": "0.1.0",
            "orgs": {"CPL": "Clinical Pathology Laboratories (demo contract)",
                     "TRI": "TriCore Reference Laboratories (demo contract)",
                     "NDX": "NorDx (demo contract)"},
            "synthetic_only": True,
            "hidden_truth_separated": True,
            "tables": {
                "bills": {"rows": table_counts.get("bills", 0)},
                "events": {"rows": table_counts.get("events", 0)},
                "allocations": {"rows": table_counts.get("allocations", 0)},
                "observation_windows": {"rows": table_counts.get("observation_windows", 0)},
            },
        }
        with open(os.path.join(out_dir, "data_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
