"""Build the Criterion (E) exhibit book from the evidence set.

Structure:
  Cover (title, criterion, beneficiary, release) ->
  Master index (exhibit number, title, page) ->
  Section dividers (E1 method / E2 tool / E3 personal role / E4 verification) ->
  Each exhibit preceded by its own cover page ->
  Continuous page numbers -> PDF bookmarks.

A4 (595x842pt), Times New Roman, per filing standards.

Usage:
    python scripts/build_exhibit_book.py
Output:
    evidence/filing/Exhibit_Book_Criterion_E_Yajie_Xu.pdf
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fitz  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILING = os.path.join(ROOT, "evidence", "filing")
OUT = os.path.join(FILING, "Exhibit_Book_Criterion_E_Yajie_Xu.pdf")

TNR = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"

EXHIBITS = [
    # (section, exhibit no, title, filename, description)
    ("E1", "Exhibit 1", "Method Report", "E1-01_method_report.pdf",
     "Method report v2.0: research questions, related work, data, event "
     "dictionary and prediction target, candidate methods, splits and "
     "leakage control, results, limitations."),
    ("E1", "Exhibit 2", "Prior Work Comparison", "E1-02_prior_work.pdf",
     "Nine verified references across record linkage, claims prediction and "
     "competing-risk literature, with overlap and difference analysis."),
    ("E1", "Exhibit 3", "Candidate Method Designs", "E1-03_candidate_methods.pdf",
     "Candidate methods with pseudocode-level specification, inputs/outputs, "
     "failure conditions and evaluation plan."),
    ("E1", "Exhibit 4", "Research Protocol and Change Record", "E1-04_protocol_and_changes.pdf",
     "Frozen research protocol (target definition, splits, metrics, "
     "conclusion conditions) and the versioned protocol change record."),
    ("E2", "Exhibit 5", "Tool Implementation — Linkage Rules", "E2-01a_code_rules.pdf",
     "Constrained linkage rules (R2 version chains, R3 weak-evidence "
     "candidates with uniqueness gating), with git blob reference."),
    ("E2", "Exhibit 6", "Tool Implementation — Amount Engine", "E2-01b_code_amounts.pdf",
     "Amount engine: gross/reversed/net/unallocated with over-allocation "
     "blocking and unresolvable-reversal flagging."),
    ("E2", "Exhibit 7", "Tool Implementation — Snapshot and Labeling", "E2-01c_code_snapshot.pdf",
     "Snapshot construction and outcome labeling with as-of discipline and "
     "censoring rules."),
    ("E2", "Exhibit 8", "Tool Implementation — Models", "E2-01d_code_models.pdf",
     "Discrete-time competing-event models (B0 baseline, B1 multinomial, "
     "C1 quality-augmented) with product-rule cumulative curves."),
    ("E2", "Exhibit 9", "Repository — Home", "E2-02a_gh01_repo_home.pdf",
     "Public repository home page (printed with URL and access date)."),
    ("E2", "Exhibit 10", "Repository — Commit History", "E2-02b_gh02_commit_history.pdf",
     "Three-year commit history (2023-2026) as publicly verifiable on the "
     "repository."),
    ("E2", "Exhibit 11", "Repository — Releases", "E2-02c_gh03_tags.pdf",
     "Versioned releases v0.2.0 through v1.4.0 with their dates."),
    ("E2", "Exhibit 12", "Repository — Representative Code", "E2-02d_gh04_code_rules.pdf",
     "Representative source file as published on the repository."),
    ("E2", "Exhibit 13", "Interface — Project and Data Status", "E2-03d_interface_app_status_202501.pdf",
     "Application capture: project and data status page."),
    ("E2", "Exhibit 14", "Interface — Event Reconstruction", "E2-03b_interface_app_reconstruction_202501.pdf",
     "Application capture: reconstruction page with lineage, link and "
     "conflict views."),
    ("E2", "Exhibit 15", "Interface — Manual Review", "E2-03c_interface_app_review_queue_202501.pdf",
     "Application capture: manual review queue."),
    ("E2", "Exhibit 16", "Interface — Delay Early-Warning", "E2-03a_interface_app_delay_early_warning_202501.pdf",
     "Application capture: prediction page with model comparison."),
    ("E3", "Exhibit 17", "Research Decision Records", "E3-01_decision_records.pdf",
     "Narrative decision records D01-D06 and PC01: background, alternatives, "
     "rationale, corresponding implementation, verification."),
    ("E3", "Exhibit 18", "Version History", "E3-02_changelog.pdf",
     "Changelog 0.0.1 through 1.4.0 with environment migrations and "
     "maintenance iterations."),
    ("E4", "Exhibit 19", "Validation Against Held-Out Adjudicated Labels", "E4-01_validation_report.pdf",
     "Module A precision/recall/refusal against held-out adjudicated "
     "adjacency; Module B model comparison and ablations."),
    ("E4", "Exhibit 20", "Acceptance Test Report", "E4-02_test_report.pdf",
     "Acceptance suites T01-T25 with observed outcomes."),
    ("E4", "Exhibit 21", "Data Card", "E4-03_data_card.pdf",
     "Dataset formation, tables, data-quality handling and curation rules."),
    ("E4", "Exhibit 22", "Data Sample — Bills", "E4-04a_sample_bills.pdf",
     "De-identified bills table, first rows."),
    ("E4", "Exhibit 23", "Data Sample — Events", "E4-04b_sample_events.pdf",
     "De-identified events table, first rows."),
    ("E4", "Exhibit 24", "Data Sample — Allocations", "E4-04c_sample_allocations.pdf",
     "De-identified allocations table, first rows."),
]


def _font(page):
    return page.insert_font(fontname="TNR", fontfile=TNR)


def _text(page, x, y, text, size=10.0, bold=False, color=(0, 0, 0)):
    page.insert_text((x, y), text, fontsize=size, fontname="TNR", color=color)


def _ctext(page, y, text, size=10.0, width=595.0):
    w = fitz.Font(fontfile=TNR).text_length(text, fontsize=size)
    page.insert_text(((width - w) / 2, y), text, fontsize=size, fontname="TNR")


def make_cover() -> fitz.Document:
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _ctext(p, 110, "EXHIBIT BOOK", size=22)
    _ctext(p, 140, "Criterion (E) — Original Scientific or Scholarly", size=13)
    _ctext(p, 158, "Research Contributions to the Academic Field", size=13)
    _ctext(p, 180, "8 C.F.R. § 204.5(i)(3)(i)(E)", size=11)
    y = 240
    _ctext(p, y, "Billing Event Reconstruction and", size=14)
    _ctext(p, y + 18, "Payment-Delay Early-Warning for", size=14)
    _ctext(p, y + 36, "Clinical Laboratory Settings", size=14)
    y = 330
    _ctext(p, y, "Beneficiary: Yajie Xu", size=12)
    _ctext(p, y + 18, "Tool release: v1.4.0 (release candidate 2026-09-14; tagged 2026-09-22)", size=11)
    _ctext(p, y + 34, "24 exhibits · sections E1-E4", size=11)
    return d


def make_index_page(page_map: dict[str, int]) -> fitz.Document:
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _text(p, 56, 60, "Master Index of Exhibits", size=15)
    y = 100
    for section in ("E1", "E2", "E3", "E4"):
        _text(p, 56, y, _section_title(section), size=11)
        y += 18
        for (sec, no, title, fn, desc) in EXHIBITS:
            if sec != section or no not in page_map:
                continue
            _text(p, 70, y, f"{no}", size=10)
            _text(p, 130, y, title[:48], size=10)
            _text(p, 500, y, str(page_map[no]), size=10)
            y += 16
        y += 8
    _text(p, 56, 800, "All exhibits are original artifacts of the referenced tool release.", size=8)
    return d


def _section_title(section: str) -> str:
    return {
        "E1": "E1 — Method and Originality Position (Exhibits 1–4)",
        "E2": "E2 — The Tool Itself (Exhibits 5–16)",
        "E3": "E3 — Personal Role (Exhibits 17–18)",
        "E4": "E4 — Verification (Exhibits 19–24)",
    }[section]


def make_divider(section: str) -> fitz.Document:
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _text(p, 56, 400, _section_title(section), size=16)
    return d


def make_exhibit_cover(no: str, title: str, desc: str) -> fitz.Document:
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _text(p, 56, 110, no, size=20)
    _text(p, 56, 150, title, size=14)
    # description wrapped
    words = desc.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) > 78:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    y = 200
    for ln in lines:
        _text(p, 56, y, ln, size=9.5)
        y += 14
    return d


def normalize_to_a4(src: fitz.Document) -> fitz.Document:
    """Center every page on A4 (595x842pt), scaling letter-size and
    slightly-off A4 pages uniformly."""
    out = fitz.open()
    for page in src:
        r = page.rect
        if abs(r.width - 595) < 0.5 and abs(r.height - 842) < 0.5:
            out.insert_pdf(src, from_page=page.number, to_page=page.number)
            continue
        scale = min(595 / r.width, 842 / r.height)
        w, h = r.width * scale, r.height * scale
        np = out.new_page(width=595, height=842)
        rect = fitz.Rect((595 - w) / 2, (842 - h) / 2, (595 + w) / 2, (842 + h) / 2)
        np.show_pdf_page(rect, src, page.number)
    return out


def main() -> int:
    book = fitz.open()
    page_map: dict[str, int] = {}

    # cover (page 1)
    book.insert_pdf(make_cover())

    # assemble all exhibits; record where each exhibit's cover starts.
    # +1 for the index page that is inserted after the cover below.
    parts: dict[str, fitz.Document] = {}
    current_section = None
    for (section, no, title, fn, desc) in EXHIBITS:
        src = os.path.join(FILING, fn)
        if not os.path.exists(src):
            print("MISSING", fn)
            continue
        if section != current_section:
            book.insert_pdf(make_divider(section))
            current_section = section
        part = fitz.open()
        part.insert_pdf(make_exhibit_cover(no, title, desc))
        part.insert_pdf(normalize_to_a4(fitz.open(src)))
        parts[no] = part
        page_map[no] = book.page_count + 2
        book.insert_pdf(part)

    # insert master index right after the cover (becomes page 2)
    idx = make_index_page(page_map)
    book.insert_pdf(idx, start_at=1)

    # continuous page numbers in footer (final layout)
    for i in range(book.page_count):
        page = book[i]
        _font(page)
        y = page.rect.height - 24
        _text(page, 300, y, f"Exhibit Book · Page {i + 1}", size=8, color=(0.3, 0.3, 0.3))

    # bookmarks
    toc = []
    for (section, no, title, fn, desc) in EXHIBITS:
        if no in page_map:
            toc.append([1, f"{no} — {title}", page_map[no]])
    book.set_toc(toc)
    book.save(OUT, garbage=4, deflate=True)
    print(f"Exhibit book: {OUT} ({book.page_count} pages, {len(toc)} bookmarks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
