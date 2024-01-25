"""Normalization layer (module A input stage).

Raw CSV rows become normalized records with parsed datetimes (UTC), integer
amounts, and the explicit event dictionary. Invalid rows are isolated, never
deleted and never silently repaired.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NormalizationIssue:
    row_ref: str
    field: str
    problem: str


@dataclass
class NormalizedTables:
    bills: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    allocations: list[dict] = field(default_factory=list)
    observation_windows: list[dict] = field(default_factory=list)
    invalid_rows: list[dict] = field(default_factory=list)
    issues: list[NormalizationIssue] = field(default_factory=list)


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None  # timezone-less timestamps are contract violations
    return dt.astimezone(timezone.utc)


def parse_amt(value: str) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def normalize_bills(text: str) -> tuple[list[dict], list[dict], list[NormalizationIssue]]:
    valid, invalid, issues = [], [], []
    for i, row in enumerate(_read_csv(text), start=2):
        sub = parse_dt(row.get("submitted_at", ""))
        ava = parse_dt(row.get("available_at", ""))
        amt = parse_amt(row.get("billed_amount_minor", ""))
        if sub is None or ava is None or amt is None or amt <= 0 or row.get("currency", "") != "USD":
            invalid.append(row)
            issues.append(NormalizationIssue(f"row{i}", "bill-fields", "invalid bill row isolated"))
            continue
        out = dict(row)
        out["submitted_at"] = sub
        out["available_at"] = ava
        out["billed_amount_minor"] = amt
        valid.append(out)
    return valid, invalid, issues


def normalize_events(text: str) -> tuple[list[dict], list[dict], list[NormalizationIssue]]:
    valid, invalid, issues = [], [], []
    for i, row in enumerate(_read_csv(text), start=2):
        eva = parse_dt(row.get("event_at", ""))
        ava = parse_dt(row.get("available_at", ""))
        if eva is None or ava is None:
            invalid.append(row)
            issues.append(NormalizationIssue(f"row{i}", "event-time", "invalid event row isolated"))
            continue
        amt = parse_amt(row.get("amount_minor", ""))
        cur = row.get("currency", "")
        if amt is not None and amt < 0:
            invalid.append(row)
            issues.append(NormalizationIssue(f"row{i}", "amount", "negative event amount isolated"))
            continue
        out = dict(row)
        out["event_at"] = eva
        out["available_at"] = ava
        out["amount_minor"] = amt
        out["currency"] = cur
        valid.append(out)
    return valid, invalid, issues


def normalize_allocations(text: str) -> tuple[list[dict], list[dict], list[NormalizationIssue]]:
    valid, invalid, issues = [], [], []
    for i, row in enumerate(_read_csv(text), start=2):
        ava = parse_dt(row.get("available_at", ""))
        amt = parse_amt(row.get("allocated_amount_minor", ""))
        if ava is None or amt is None or amt <= 0 or row.get("currency", "") != "USD":
            invalid.append(row)
            issues.append(NormalizationIssue(f"row{i}", "allocation-fields", "invalid allocation row isolated"))
            continue
        out = dict(row)
        out["available_at"] = ava
        out["allocated_amount_minor"] = amt
        valid.append(out)
    return valid, invalid, issues


def normalize_observation_windows(text: str) -> tuple[list[dict], list[dict], list[NormalizationIssue]]:
    valid, invalid, issues = [], [], []
    for i, row in enumerate(_read_csv(text), start=2):
        cs = parse_dt(row.get("coverage_start", ""))
        ce = parse_dt(row.get("coverage_end", ""))
        ex = parse_dt(row.get("extracted_at", ""))
        if cs is None or ce is None or ex is None or ce < cs:
            invalid.append(row)
            issues.append(NormalizationIssue(f"row{i}", "window", "invalid observation window isolated"))
            continue
        out = dict(row)
        out["coverage_start"] = cs
        out["coverage_end"] = ce
        out["extracted_at"] = ex
        valid.append(out)
    return valid, invalid, issues
