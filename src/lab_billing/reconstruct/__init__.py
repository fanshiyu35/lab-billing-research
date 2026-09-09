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
        self.amounts: dict = {}
        self.duplicate_event_ids: set[str] = set()

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
        if self.as_of is not None:
            bills = [b for b in bills if b["available_at"] <= self.as_of]
            events = [e for e in events if e["available_at"] <= self.as_of]
            allocs = [a for a in allocs if a["available_at"] <= self.as_of]
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

    def dedup_events(self) -> None:
        """Duplicate event imports: identical business content under
        different event ids is flagged; the duplicate is excluded from
        amount computation so payments are not double-counted."""
        key = lambda e: (e["org_token"], e["source_system"], e["bill_record_id"],
                         e["event_type"], e["event_at"], e.get("amount_minor"),
                         e.get("currency"))
        seen: dict[tuple, str] = {}
        for e in self.events:
            k = key(e)
            if k in seen:
                self.conflicts.append(_conflict_row(
                    "DUPLICATE_IMPORT", [seen[k], e["event_id"]],
                    "identical event content imported twice", self.run_id))
                self.duplicate_event_ids.add(e["event_id"])
            else:
                seen[k] = e["event_id"]
        self.audit.append(AuditEntry("dedup_events", "duplicate event imports flagged", {
            "duplicates": len(self.duplicate_event_ids),
        }))

    # -------------------------------------------------------------- exact id
    def link_exact_ids(self) -> None:
        """Native previous_record_id references with sanity checks."""
        for b in self.bills:
            prev_id = (b.get("previous_record_id") or "").strip()
            if not prev_id:
                continue
            self._link_pair(prev_id, b["record_id"], rule_id="R1_native_previous_id")

    # --------------------------------------------------------- constrained
    def link_constrained(self) -> None:
        """R2 version chains and R3 weak-evidence candidates (v0.7)."""
        from .rules import generate_r2_candidates, generate_r3_candidates, resolve_r3

        for c in generate_r2_candidates(self.bills):
            if c.to_id == "":  # ambiguous version set
                self.review_queue.append(_review_row(
                    "AMBIGUOUS_VERSION_SET", [c.from_id],
                    c.evidence, self.run_id))
                continue
            self._link_pair(c.from_id, c.to_id, rule_id=c.rule_id,
                            reason=c.evidence, score=c.score,
                            score_kind=c.score_kind)

        accepted, review = resolve_r3(generate_r3_candidates(self.bills))
        for c in accepted:
            self._link_pair(c.from_id, c.to_id, rule_id=c.rule_id,
                            reason=c.evidence, score=c.score,
                            score_kind=c.score_kind)
        for c in review:
            self.review_queue.append(_review_row(
                "MULTI_CANDIDATE_AMBIGUITY", [c.from_id, c.to_id],
                c.evidence, self.run_id))

    def _link_pair(self, from_id: str, to_id: str, rule_id: str,
                   reason: str = "native explicit predecessor reference",
                   score: str | float = "", score_kind: str = "NOT_SCORED") -> None:
        if any(l["left_record_id"] == from_id and l["right_record_id"] == to_id
               for l in self.links):
            return  # already linked by a higher-priority rule
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
        # time order sanity: only meaningful for explicit predecessors and
        # version chains (R1/R2); R3 weak-evidence pairs are same-lineage
        # candidates without an inherent ordering
        if rule_id in ("R1_native_previous_id", "R2_same_bill_id_versions"):
            if src["submitted_at"] > dst["submitted_at"]:
                self.conflicts.append(_conflict_row(
                    "TIME_ORDER_VIOLATION", [from_id, to_id],
                    f"{rule_id}: predecessor submitted after successor", self.run_id))
        self.links.append({
            "run_id": self.run_id,
            "as_of": _fmt(self.as_of) if self.as_of else "",
            "method_version": self.method_version,
            "left_record_id": from_id,
            "right_record_id": to_id,
            "decision": "accepted",
            "rule_ids": rule_id,
            "reason": reason,
            "score": str(score),
            "score_kind": score_kind,
            "review_required": "false",
        })

    # -------------------------------------------------- transitive conflicts
    def detect_transitive_conflicts(self) -> None:
        """Detect conflicting chains: a record claimed by two different
        predecessors, or time-order contradictions along a chain."""
        children: dict[str, list[dict]] = defaultdict(list)
        for link in self.links:
            children[link["left_record_id"]].append(link)
        for from_id, links in children.items():
            if len(links) > 1:
                self.conflicts.append(_conflict_row(
                    "MULTIPLE_SUCCESSOR", [from_id],
                    "one record is the predecessor of several distinct successors",
                    self.run_id))

    # ------------------------------------------------------ manual decisions
    def apply_manual_decisions(self, data_dir: str) -> None:
        """manual_decisions.csv: human adjudications applied as a separate
        layer; automatic output and post-adjudication state are kept apart."""
        import csv as _csv

        path = os.path.join(data_dir, "manual_decisions.csv")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                decision = (row.get("decision") or "").strip().lower()
                if decision != "link":
                    continue
                frm = (row.get("left_record_id") or "").strip()
                to = (row.get("right_record_id") or "").strip()
                if not frm or not to:
                    continue
                self._link_pair(frm, to, rule_id="M1_manual_decision",
                                reason=f"human adjudication by {row.get('operator', 'unknown')}",
                                score="", score_kind="HUMAN_ADJUDICATED")

    def compute_amounts(self) -> None:
        from .amounts import AmountEngine

        lineage_of_record: dict[str, str] = {}
        for lin in self.lineages:
            for rid in lin["record_ids"].split("|"):
                if rid:
                    lineage_of_record[rid] = lin["lineage_id"]
        eng = AmountEngine(self.run_id)
        visible_events = [e for e in self.events
                          if e["event_id"] not in self.duplicate_event_ids]
        result = eng.compute(visible_events, self.allocs, lineage_of_record)
        for lin in self.lineages:
            acc = result.get(lin["lineage_id"])
            if acc is None:
                continue
            lin["gross_posted"] = str(acc.gross_posted)
            lin["reversed"] = str(acc.reversed)
            lin["net_observed_posted"] = str(acc.net_observed_posted)
            lin["unallocated"] = str(acc.unallocated)
            if lin["status"] == "OPEN" and acc.gross_posted > 0:
                lin["status"] = "PAYMENT_OBSERVED"
            elif lin["status"] == "CLOSED_NO_PAYMENT" and acc.gross_posted > 0:
                lin["status"] = "REOPENED_OR_POST_CLOSE_PAYMENT"
        for c in eng.conflicts:
            self.conflicts.append(_conflict_row(
                c.kind, c.event_ids, c.detail, self.run_id))
        self.amounts = {k: {
            "gross_posted": v.gross_posted,
            "reversed": v.reversed,
            "net_observed_posted": v.net_observed_posted,
            "unallocated": v.unallocated,
        } for k, v in result.items()}
        self.audit.append(AuditEntry("amounts", "amount engine v1.0", {
            "lineages_with_amounts": len(result),
        }))

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
        payer_cat = {
            "AET": "commercial", "UHC": "commercial", "HUM": "commercial",
            "BCB": "commercial", "CIG": "commercial",
            "MCR": "government", "MCD": "government", "SELF": "self", "": "unknown",
        }
        coverage_by_org: dict[str, dict] = {}
        for w in self.windows:
            if w.get("coverage_status") == "complete":
                coverage_by_org[w["org_token"]] = w

        for lin, members in groups.items():
            member_bills = [self.bill_index[m] for m in members if m in self.bill_index]
            payer_tokens = {b.get("payer_token", "") for b in member_bills}
            latest = max(member_bills, key=lambda b: b["submitted_at"]) if member_bills else None
            cov = coverage_by_org.get(self.bill_index[lin]["org_token"], {})
            self.lineages.append({
                "run_id": self.run_id,
                "lineage_id": f"run-{lin[:8]}-{lin}",
                "record_ids": "|".join(sorted(members)),
                "org_token": self.bill_index[lin]["org_token"],
                "status": self._lineage_status(lin, members),
                "payer_category": payer_cat.get(
                    next(iter(payer_tokens - {""}), "") if payer_tokens else "", "unknown"),
                "billed_amount_minor": str(latest["billed_amount_minor"]) if latest else "0",
                "conflict_count": "0",
                "review_count": "0",
                "coverage_status": cov.get("coverage_status", "unknown"),
                "coverage_end": cov.get("coverage_end", ""),
                "gross_posted": "0",
                "reversed": "0",
                "net_observed_posted": "0",
                "unallocated": "0",
            })
        # post-hoc counts for conflicts/reviews touching each lineage
        for lin in self.lineages:
            ids = set(lin["record_ids"].split("|"))
            lin["conflict_count"] = str(sum(
                1 for c in self.conflicts
                if any(rid in ids for rid in c.get("record_ids", "").split("|"))))
            lin["review_count"] = str(sum(
                1 for r in self.review_queue
                if any(rid in ids for rid in r.get("record_ids", "").split("|"))))

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
        self.dedup_events()
        self.link_exact_ids()
        self.link_constrained()
        self.apply_manual_decisions(data_dir)
        self.detect_transitive_conflicts()
        self.build_lineages()
        self.compute_amounts()
        os.makedirs(out_dir, exist_ok=True)
        _write_csv(os.path.join(out_dir, "lineages.csv"), self.lineages)
        _write_csv(os.path.join(out_dir, "links.csv"), self.links)
        _write_csv(os.path.join(out_dir, "conflicts.csv"), self.conflicts)
        _write_csv(os.path.join(out_dir, "review_queue.csv"), self.review_queue)
        _write_csv(os.path.join(out_dir, "events_normalized.csv"),
                   [_ev_norm(e) for e in self.events])
        _write_csv(os.path.join(out_dir, "allocations_normalized.csv"),
                   [_al_norm(a) for a in self.allocs])
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


def _al_norm(a: dict) -> dict:
    return {
        "allocation_id": a["allocation_id"],
        "payment_event_id": a["payment_event_id"],
        "bill_record_id": a["bill_record_id"],
        "allocated_amount_minor": a["allocated_amount_minor"],
        "currency": a["currency"],
        "available_at": _fmt(a["available_at"]),
        "source_ref": a["source_ref"],
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
