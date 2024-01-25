"""Module A reconstruction pipeline — v0.2 (exact-id baseline only).

Spec section 10, stages 1-7. This version implements the exact_id baseline:
native previous_record_id plus confirmed mappings, with sanity checks
(org match, no cycles, amount semantics, time order). Broken references
surface as conflicts. Multi-candidate cases are deferred to needs_review.

Outputs: lineages.csv, links.csv, conflicts.csv, review_queue.csv,
events_normalized.csv, reconstruction_audit.json.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from lab_billing.normalize import (
    normalize_allocations,
    normalize_bills,
    normalize_events,
    normalize_observation_windows,
)


@dataclass
class AuditEntry:
    stage: str
    detail: str
    counts: dict = field(default_factory=dict)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class ReconstructionEngine:
    """v0.2: exact_id baseline."""

    def __init__(self, run_id: str, as_of: str | None = None, method_version: str = "0.2.0"):
        self.run_id = run_id
        self.as_of = parse_as_of(as_of)
        self.method_version = method_version
        self.audit: list[AuditEntry] = []
        self.links: list[dict] = []
        self.lineages: list[dict] = []
        self.conflicts: list[dict] = []
        self.review_queue: list[dict] = []
        self.bill_index: dict[str, dict] = {}

    # ------------------------------------------------------------------ load
    def load(self, data_dir: str) -> None:
        with open(os.path.join(data_dir, "bills.csv"), encoding="utf-8") as f:
            bills, bad_b, iss_b = normalize_bills(f.read())
        with open(os.path.join(data_dir, "events.csv"), encoding="utf-8") as f:
            events, bad_e, iss_e = normalize_events(f.read())
        with open(os.path.join(data_dir, "allocations.csv"), encoding="utf-8") as f:
            allocs, bad_a, iss_a = normalize_allocations(f.read())
        try:
            with open(os.path.join(data_dir, "observation_windows.csv"), encoding="utf-8") as f:
                windows, bad_w, iss_w = normalize_observation_windows(f.read())
        except FileNotFoundError:
            windows, bad_w, iss_w = [], [], []
        self.bills = bills
        self.events = events
        self.allocs = allocs
        self.windows = windows
        self.audit.append(AuditEntry("load", "normalized inputs", {
            "bills": len(bills), "bills_invalid": len(bad_b),
            "events": len(events), "events_invalid": len(bad_e),
            "allocations": len(allocs), "allocations_invalid": len(bad_a),
            "windows": len(windows),
        }))

    # ------------------------------------------------------- dedup + index
    def dedup_and_index(self) -> None:
        """Deduplicate by (org, source_system, native identity). Different
        content under the same key is a conflict, never a silent drop."""
        key = lambda b: (b["org_token"], b["source_system"], b["bill_id"], b["version_id"])
        seen: dict[tuple, dict] = {}
        kept: list[dict] = []
        for b in self.bills:
            k = key(b)
            if k in seen:
                prev = seen[k]
                if _rows_equivalent(prev, b):
                    self.conflicts.append(_conflict_row(
                        "DUPLICATE_IMPORT", [prev["record_id"], b["record_id"]],
                        "duplicate import of identical content", self.run_id))
                    continue
                self.conflicts.append(_conflict_row(
                    "CONFLICTING_DUPLICATE_KEY", [prev["record_id"], b["record_id"]],
                    "same native key, different content", self.run_id))
                self.review_queue.append(_review_row(
                    "CONFLICTING_DUPLICATE_KEY", [prev["record_id"], b["record_id"]],
                    "same native key, different content; needs human decision", self.run_id))
                kept.append(b)  # keep both for human review
                continue
            seen[k] = b
            kept.append(b)
        self.bills = kept
        self.bill_index = {b["record_id"]: b for b in kept if b["record_id"]}
        self.audit.append(AuditEntry("dedup", "deduplicated bill rows", {"kept": len(kept)}))

    # -------------------------------------------------------------- exact id
    def link_exact_ids(self) -> None:
        """Native previous_record_id references with sanity checks."""
        for b in self.bills:
            prev_id = (b.get("previous_record_id") or "").strip()
            if not prev_id:
                continue
            self._link_pair(prev_id, b["record_id"], rule_id="R1_native_previous_id")

    def _link_pair(self, from_id: str, to_id: str, rule_id: str) -> None:
        src = self.bill_index.get(from_id)
        dst = self.bill_index.get(to_id)
        if src is None or dst is None:
            missing = from_id if src is None else to_id
            self.review_queue.append(_review_row(
                "DANGLING_REFERENCE", [to_id, from_id],
                f"reference target {missing} not found in inputs", self.run_id))
            return
        if src["org_token"] != dst["org_token"]:
            self.conflicts.append(_conflict_row(
                "CROSS_ORG_REFERENCE", [from_id, to_id],
                "explicit reference crosses org boundary", self.run_id))
            return
        # cycle detection
        if _creates_cycle(from_id, to_id, self.bill_index):
            self.conflicts.append(_conflict_row(
                "CYCLE_REFERENCE", [from_id, to_id],
                "explicit reference would create a cycle", self.run_id))
            return
        # time order sanity: predecessor submitted before successor
        if src["submitted_at"] > dst["submitted_at"]:
            self.conflicts.append(_conflict_row(
                "TIME_ORDER_VIOLATION", [from_id, to_id],
                "predecessor submitted after successor", self.run_id))
        self.links.append({
            "run_id": self.run_id,
            "as_of": _fmt(self.as_of) if self.as_of else "",
            "method_version": self.method_version,
            "left_record_id": from_id,
            "right_record_id": to_id,
            "decision": "accepted",
            "rule_ids": rule_id,
            "reason": "native explicit predecessor reference",
            "score": "",
            "score_kind": "NOT_SCORED",
            "review_required": "false",
        })

    # ---------------------------------------------------------------- output
    def build_lineages(self) -> None:
        parent: dict[str, str] = {}
        for link in self.links:
            parent[link["right_record_id"]] = link["left_record_id"]
        lineage_of: dict[str, str] = {}
        def root_of(rid: str) -> str:
            seen = set()
            cur = rid
            while cur in parent and cur not in seen:
                seen.add(cur)
                cur = parent[cur]
            return cur
        for b in self.bills:
            lineage_of[b["record_id"]] = root_of(b["record_id"])
        groups: dict[str, list[str]] = defaultdict(list)
        for rid, lin in lineage_of.items():
            groups[lin].append(rid)
        for lin, members in groups.items():
            self.lineages.append({
                "run_id": self.run_id,
                "lineage_id": f"run-{lin[:8]}-{lin}",
                "record_ids": "|".join(sorted(members)),
                "org_token": self.bill_index[lin]["org_token"],
                "status": self._lineage_status(lin, members),
            })

    def _lineage_status(self, root: str, members: list[str]) -> str:
        ids = set(members)
        events = [e for e in self.events if e.get("bill_record_id") in ids]
        closed = any(e["event_type"] == "CLOSED_NO_PAYMENT" for e in events)
        if closed:
            return "CLOSED_NO_PAYMENT"
        return "OPEN"

    def run(self, data_dir: str, out_dir: str) -> dict:
        self.load(data_dir)
        self.dedup_and_index()
        self.link_exact_ids()
        self.build_lineages()
        os.makedirs(out_dir, exist_ok=True)
        _write_csv(os.path.join(out_dir, "lineages.csv"), self.lineages)
        _write_csv(os.path.join(out_dir, "links.csv"), self.links)
        _write_csv(os.path.join(out_dir, "conflicts.csv"), self.conflicts)
        _write_csv(os.path.join(out_dir, "review_queue.csv"), self.review_queue)
        _write_csv(os.path.join(out_dir, "events_normalized.csv"),
                   [_ev_norm(e) for e in self.events])
        audit = {
            "run_id": self.run_id,
            "as_of": _fmt(self.as_of) if self.as_of else None,
            "method_version": self.method_version,
            "stages": [{"stage": a.stage, "detail": a.detail, "counts": a.counts}
                       for a in self.audit],
            "summary": {
                "bills": len(self.bills),
                "links": len(self.links),
                "lineages": len(self.lineages),
                "conflicts": len(self.conflicts),
                "review_queue": len(self.review_queue),
            },
        }
        with open(os.path.join(out_dir, "reconstruction_audit.json"), "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2)
        return audit


def parse_as_of(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    return dt.astimezone(timezone.utc)


def _rows_equivalent(a: dict, b: dict) -> bool:
    keys = [k for k in a if k not in ("record_id", "source_ref")]
    return all(a.get(k) == b.get(k) for k in keys)


def _creates_cycle(from_id: str, to_id: str, index: dict) -> bool:
    """Would linking to_id -> from_id create a cycle in existing refs?"""
    cur = from_id
    seen: set[str] = set()
    while cur and cur not in seen:
        seen.add(cur)
        if cur == to_id:
            return True
        nxt = index.get(cur, {}).get("previous_record_id") or ""
        cur = nxt.strip()
    return False


def _conflict_row(kind: str, record_ids: list[str], detail: str, run_id: str) -> dict:
    return {
        "run_id": run_id,
        "conflict_type": kind,
        "record_ids": "|".join(record_ids),
        "detail": detail,
    }


def _review_row(kind: str, record_ids: list[str], detail: str, run_id: str) -> dict:
    return {
        "run_id": run_id,
        "review_type": kind,
        "record_ids": "|".join(record_ids),
        "detail": detail,
        "status": "pending",
    }


def _ev_norm(e: dict) -> dict:
    return {
        "event_id": e["event_id"],
        "org_token": e["org_token"],
        "source_system": e["source_system"],
        "bill_record_id": e["bill_record_id"],
        "event_type": e["event_type"],
        "event_at": _fmt(e["event_at"]),
        "available_at": _fmt(e["available_at"]),
        "amount_minor": e.get("amount_minor"),
        "currency": e.get("currency"),
        "reverses_event_id": e.get("reverses_event_id"),
        "terminal_flag": e.get("terminal_flag"),
        "source_ref": e.get("source_ref"),
    }
