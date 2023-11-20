"""Explicit event dictionary (spec section 08).

Mapping raw source statuses to these event types must preserve the raw code
and the mapping basis; unmappable codes become UNKNOWN and enter review.
"""
from __future__ import annotations

EVENT_TYPES = (
    "SUBMITTED",
    "CORRECTED",
    "PAYMENT_POSTED",
    "PAYMENT_REVERSED",
    "VOID_VERSION",
    "CLOSED_NO_PAYMENT",
    "REOPENED",
    "ADJUSTMENT",
    "STATUS_UPDATED",
    "UNKNOWN",
)

EVENT_SEMANTICS = {
    "SUBMITTED": {
        "description": "Bill version submitted to payer or internal adjudication.",
        "amount_semantics": "billed amount of this version",
        "terminal": False,
    },
    "CORRECTED": {
        "description": "New version of a prior bill version was created.",
        "amount_semantics": "new billed amount",
        "terminal": False,
    },
    "PAYMENT_POSTED": {
        "description": "Payment posted; may be allocated to one or more bills.",
        "amount_semantics": "posted payment amount (gross)",
        "terminal": False,
    },
    "PAYMENT_REVERSED": {
        "description": "Reversal of a previously posted payment event.",
        "amount_semantics": "reversed amount (negative direction)",
        "terminal": False,
    },
    "VOID_VERSION": {
        "description": "A specific bill version is voided; the lineage may continue.",
        "amount_semantics": "voided version amount",
        "terminal": False,
    },
    "CLOSED_NO_PAYMENT": {
        "description": "Explicit termination of the lineage with no payment.",
        "amount_semantics": "none",
        "terminal": True,
    },
    "REOPENED": {
        "description": "A closed lineage is reopened; older close events are retained.",
        "amount_semantics": "none",
        "terminal": False,
    },
    "ADJUSTMENT": {
        "description": "Contractual or administrative adjustment; not a payment.",
        "amount_semantics": "adjustment amount",
        "terminal": False,
    },
    "STATUS_UPDATED": {
        "description": "Non-financial status change.",
        "amount_semantics": "none",
        "terminal": False,
    },
    "UNKNOWN": {
        "description": "Unmappable source status; kept for review.",
        "amount_semantics": "unknown",
        "terminal": False,
    },
}


def terminal_event_types() -> tuple[str, ...]:
    return tuple(t for t, s in EVENT_SEMANTICS.items() if s["terminal"])


def is_known_event_type(event_type: str) -> bool:
    return event_type in EVENT_TYPES
