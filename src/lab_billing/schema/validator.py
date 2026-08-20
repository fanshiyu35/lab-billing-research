"""Input validation for the five table contracts (spec section 07).

Validation isolates invalid rows; it never deletes source records and never
silently repairs values. All findings are reported with row references.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Finding:
    row_ref: str
    field: str
    problem: str
    severity: str  # ERROR / WARNING


@dataclass
class ValidationResult:
    table: str
    findings: list[Finding] = field(default_factory=list)
    valid_row_count: int = 0
    invalid_row_count: int = 0

    @property
    def ok(self) -> bool:
        return not any(f.severity == "ERROR" for f in self.findings)

    def report(self) -> str:
        lines = [f"{self.table}: {self.valid_row_count} valid, {self.invalid_row_count} invalid"]
        for f in self.findings:
            lines.append(f"  [{f.severity}] {f.row_ref} {f.field}: {f.problem}")
        return "\n".join(lines)


_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_ORG_OK_DEFAULT = {"CPL", "TRI", "NDX"}
_PAYER_OK_DEFAULT = {"AET", "UHC", "HUM", "BCB", "CIG", "MCR", "MCD", "SELF", ""}


def _org_ok(row: dict, extra: set | None) -> bool:
    ok = set(_ORG_OK_DEFAULT)
    if extra:
        ok |= extra
    return row.get("org_token", "") in ok


def _payer_ok(row: dict, extra: set | None) -> bool:
    ok = set(_PAYER_OK_DEFAULT)
    if extra:
        ok |= extra
    return row.get("payer_token", "") in ok
_CURRENCY_OK = {"USD"}


def _iso(s: str) -> bool:
    return bool(s) and bool(_ISO_RE.match(s))


def _tz_ok(s: str) -> bool:
    """Timestamps without timezone are rejected unless explicitly confirmed."""
    return _iso(s) and (s.endswith("Z") or bool(re.search(r"[+-]\d{2}:\d{2}$", s)))


def _int_pos(s: str) -> bool:
    try:
        return int(s) > 0
    except (TypeError, ValueError):
        return False


def _int_nonneg(s: str) -> bool:
    try:
        return int(s) >= 0
    except (TypeError, ValueError):
        return False


def _parsed(s: str):
    if s.endswith("Z"):
        s2 = s[:-1] + "+00:00"
    else:
        s2 = s
    try:
        return datetime.fromisoformat(s2)
    except ValueError:
        return None


def validate_bills(text: str, extra_orgs: set | None = None,
                  extra_payers: set | None = None) -> ValidationResult:
    r = ValidationResult("bills")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        rid = row.get("record_id", "")
        if not _ID_RE.match(rid):
            r.findings.append(Finding(f"row{i}", "record_id", "invalid or missing", "ERROR"))
        if not _org_ok(row, extra_orgs):
            r.findings.append(Finding(f"row{i}", "org_token", "unknown org", "ERROR"))
        if not row.get("bill_id", ""):
            r.findings.append(Finding(f"row{i}", "bill_id", "missing", "ERROR"))
        if not _int_pos(row.get("billed_amount_minor", "")):
            r.findings.append(Finding(f"row{i}", "billed_amount_minor", "must be positive integer", "ERROR"))
        if row.get("currency", "") not in _CURRENCY_OK:
            r.findings.append(Finding(f"row{i}", "currency", "unsupported currency", "ERROR"))
        for f in ("submitted_at", "available_at"):
            if not _tz_ok(row.get(f, "")):
                r.findings.append(Finding(f"row{i}", f, "must be ISO 8601 with timezone", "ERROR"))
        sa, aa = _parsed(row.get("submitted_at", "")), _parsed(row.get("available_at", ""))
        if sa and aa and aa < sa:
            r.findings.append(Finding(f"row{i}", "available_at", "available before submitted", "WARNING"))
        prev = row.get("previous_record_id", "")
        if prev and not _ID_RE.match(prev):
            r.findings.append(Finding(f"row{i}", "previous_record_id", "invalid format", "ERROR"))
        pt = row.get("payer_token", "")
        if not _payer_ok(row, extra_payers):
            r.findings.append(Finding(f"row{i}", "payer_token", "unknown payer token", "WARNING"))
        if r.findings and r.findings[-1].row_ref == f"row{i}":
            invalid = any(f.severity == "ERROR" for f in r.findings if f.row_ref == f"row{i}")
        else:
            invalid = False
        r.valid_row_count += 0 if invalid else 1
        r.invalid_row_count += 1 if invalid else 0
    return r


def validate_events(text: str, extra_orgs: set | None = None,
                    extra_payers: set | None = None) -> ValidationResult:
    from .event_dict import is_known_event_type

    r = ValidationResult("events")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        rid = row.get("event_id", "")
        if not _ID_RE.match(rid):
            r.findings.append(Finding(f"row{i}", "event_id", "invalid or missing", "ERROR"))
        if not _org_ok(row, extra_orgs):
            r.findings.append(Finding(f"row{i}", "org_token", "unknown org", "ERROR"))
        et = row.get("event_type", "")
        if not is_known_event_type(et):
            r.findings.append(Finding(f"row{i}", "event_type", f"unknown type {et!r}", "ERROR"))
        if et == "UNKNOWN":
            r.findings.append(Finding(f"row{i}", "event_type", "UNKNOWN requires review", "WARNING"))
        for f in ("event_at", "available_at"):
            if not _tz_ok(row.get(f, "")):
                r.findings.append(Finding(f"row{i}", f, "must be ISO 8601 with timezone", "ERROR"))
        amt = row.get("amount_minor", "")
        if amt:
            if not _int_nonneg(amt):
                r.findings.append(Finding(f"row{i}", "amount_minor", "invalid amount", "ERROR"))
            if row.get("currency", "") not in _CURRENCY_OK:
                r.findings.append(Finding(f"row{i}", "currency", "currency required with amount", "ERROR"))
        rev = row.get("reverses_event_id", "")
        if rev and not _ID_RE.match(rev):
            r.findings.append(Finding(f"row{i}", "reverses_event_id", "invalid format", "ERROR"))
        tf = row.get("terminal_flag", "")
        if tf not in ("true", "false", "True", "False"):
            r.findings.append(Finding(f"row{i}", "terminal_flag", "must be boolean", "ERROR"))
        invalid = any(f.severity == "ERROR" for f in r.findings if f.row_ref == f"row{i}")
        r.valid_row_count += 0 if invalid else 1
        r.invalid_row_count += 1 if invalid else 0
    return r


def validate_allocations(text: str, extra_orgs: set | None = None) -> ValidationResult:
    r = ValidationResult("allocations")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        if not _ID_RE.match(row.get("allocation_id", "")):
            r.findings.append(Finding(f"row{i}", "allocation_id", "invalid or missing", "ERROR"))
        for f in ("payment_event_id", "bill_record_id"):
            if not _ID_RE.match(row.get(f, "")):
                r.findings.append(Finding(f"row{i}", f, "invalid or missing", "ERROR"))
        if not _int_pos(row.get("allocated_amount_minor", "")):
            r.findings.append(Finding(f"row{i}", "allocated_amount_minor", "must be positive integer", "ERROR"))
        if row.get("currency", "") not in _CURRENCY_OK:
            r.findings.append(Finding(f"row{i}", "currency", "unsupported currency", "ERROR"))
        if not _tz_ok(row.get("available_at", "")):
            r.findings.append(Finding(f"row{i}", "available_at", "must be ISO 8601 with timezone", "ERROR"))
        invalid = any(f.severity == "ERROR" for f in r.findings if f.row_ref == f"row{i}")
        r.valid_row_count += 0 if invalid else 1
        r.invalid_row_count += 1 if invalid else 0
    return r


def validate_observation_windows(text: str, extra_orgs: set | None = None) -> ValidationResult:
    r = ValidationResult("observation_windows")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        if not _ID_RE.match(row.get("window_id", "")):
            r.findings.append(Finding(f"row{i}", "window_id", "invalid or missing", "ERROR"))
        if not _org_ok(row, extra_orgs):
            r.findings.append(Finding(f"row{i}", "org_token", "unknown org", "ERROR"))
        for f in ("coverage_start", "coverage_end", "extracted_at"):
            if not _tz_ok(row.get(f, "")):
                r.findings.append(Finding(f"row{i}", f, "must be ISO 8601 with timezone", "ERROR"))
        cs, ce = _parsed(row.get("coverage_start", "")), _parsed(row.get("coverage_end", ""))
        if cs and ce and ce < cs:
            r.findings.append(Finding(f"row{i}", "coverage_end", "before coverage start", "ERROR"))
        if row.get("coverage_status", "") not in ("complete", "partial", "unknown"):
            r.findings.append(Finding(f"row{i}", "coverage_status", "invalid status", "ERROR"))
        invalid = any(f.severity == "ERROR" for f in r.findings if f.row_ref == f"row{i}")
        r.valid_row_count += 0 if invalid else 1
        r.invalid_row_count += 1 if invalid else 0
    return r
