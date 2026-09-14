"""Build the Criterion (E) exhibit book from the evidence set.

Structure:
  Cover (title, criterion, beneficiary, release) ->
  Certification of true copies (28 U.S.C. 1746) ->
  Master index (exhibit number, title, page) ->
  Section dividers (E1 method / E2 tool / E3 personal role / E4 verification) ->
  Each exhibit preceded by a label page (exhibit tab + provenance line) ->
  Continuous Bates numbering -> PDF bookmarks.

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
MONO = "/System/Library/Fonts/Supplemental/Courier New.ttf"

# (section, exhibit no, title, filename, description, source-anchor line)
EXHIBITS = [
    ("E1", "Exhibit 1", "Method Report", "E1-01_method_report.pdf",
     "Method report v2.0: research questions, related work, data, event "
     "dictionary and prediction target, candidate methods, splits and "
     "leakage control, results, limitations.",
     "outputs/reports/method_report_v2.0_20260922.md — v1.4.0 (release candidate 2026-09-14)"),
    ("E1", "Exhibit 2", "Prior Work Comparison", "E1-02_prior_work.pdf",
     "Nine verified references across record linkage, claims prediction and "
     "competing-risk literature, with overlap and difference analysis.",
     "research/prior_work.csv — v1.4.0 (release candidate 2026-09-14)"),
    ("E1", "Exhibit 3", "Candidate Method Designs", "E1-03_candidate_methods.pdf",
     "Candidate methods with pseudocode-level specification, inputs/outputs, "
     "failure conditions and evaluation plan.",
     "research/candidate_methods.md — v1.4.0 (release candidate 2026-09-14)"),
    ("E1", "Exhibit 4", "Research Protocol and Change Record", "E1-04_protocol_and_changes.pdf",
     "Frozen research protocol (target definition, splits, metrics, "
     "conclusion conditions) and the versioned protocol change record.",
     "research/protocol_v1_research_edition.json + research/protocol_changes.csv — v1.4.0"),
    ("E2", "Exhibit 5", "Tool Implementation — Linkage Rules", "E2-01a_code_rules.pdf",
     "Constrained linkage rules (R2 version chains, R3 weak-evidence "
     "candidates with uniqueness gating), with git blob reference.",
     "src/lab_billing/reconstruct/rules.py — git blob at v1.4.0"),
    ("E2", "Exhibit 6", "Tool Implementation — Amount Engine", "E2-01b_code_amounts.pdf",
     "Amount engine: gross/reversed/net/unallocated with over-allocation "
     "blocking and unresolvable-reversal flagging.",
     "src/lab_billing/reconstruct/amounts.py — git blob at v1.4.0"),
    ("E2", "Exhibit 7", "Tool Implementation — Snapshot and Labeling", "E2-01c_code_snapshot.pdf",
     "Snapshot construction and outcome labeling with as-of discipline and "
     "censoring rules.",
     "src/lab_billing/forecast/snapshot.py — git blob at v1.4.0"),
    ("E2", "Exhibit 8", "Tool Implementation — Models", "E2-01d_code_models.pdf",
     "Discrete-time competing-event models (B0 baseline, B1 multinomial, "
     "C1 quality-augmented) with product-rule cumulative curves.",
     "src/lab_billing/forecast/models.py — git blob at v1.4.0"),
    ("E2", "Exhibit 9", "Repository — Home", "E2-02a_gh01_repo_home.pdf",
     "Public repository home page (printed with URL and access date).",
     "github.com/fanshiyu35/lab-billing-research — printed 2026-09"),
    ("E2", "Exhibit 10", "Repository — Commit History", "E2-02b_gh02_commit_history.pdf",
     "Commit history as publicly verifiable on the repository.",
     "github.com/fanshiyu35/lab-billing-research/commits/main — printed 2026-09"),
    ("E2", "Exhibit 11", "Repository — Releases", "E2-02c_gh03_tags.pdf",
     "Versioned releases v0.2.0 through v1.4.0 with their dates.",
     "github.com/fanshiyu35/lab-billing-research/tags — printed 2026-09"),
    ("E2", "Exhibit 12", "Repository — README", "E2-02d_gh04_code_rules.pdf",
     "Representative source file as published on the repository.",
     "src/lab_billing/reconstruct/rules.py — rendered from the repository source"),
    ("E2", "Exhibit 13", "Interface — Project and Data Status", "E2-03d_interface_app_status_202501.pdf",
     "Application capture: project and data status page.",
     "evidence/screenshots/ — local interface capture, 2026-09"),
    ("E2", "Exhibit 14", "Interface — Event Reconstruction", "E2-03b_interface_app_reconstruction_202501.pdf",
     "Application capture: reconstruction page with lineage, link and "
     "conflict views.",
     "evidence/screenshots/ — local interface capture, 2026-09"),
    ("E2", "Exhibit 15", "Interface — Manual Review", "E2-03c_interface_app_review_queue_202501.pdf",
     "Application capture: manual review queue.",
     "evidence/screenshots/ — local interface capture, 2026-09"),
    ("E2", "Exhibit 16", "Interface — Delay Early-Warning", "E2-03a_interface_app_delay_early_warning_202501.pdf",
     "Application capture: prediction page with model comparison.",
     "evidence/screenshots/ — local interface capture, 2026-09"),
    ("E3", "Exhibit 17", "Research Decision Records", "E3-01_decision_records.pdf",
     "Narrative decision records D01-D06 and PC01: background, alternatives, "
     "rationale, corresponding implementation, verification.",
     "research/decisions/*.md — narrative decision records, v1.4.0"),
    ("E3", "Exhibit 18", "Version History", "E3-02_changelog.pdf",
     "Changelog 0.0.1 through 1.4.0 with environment migrations and "
     "maintenance iterations.",
     "CHANGELOG.md — v1.4.0"),
    ("E4", "Exhibit 19", "Validation Against Held-Out Adjudicated Labels", "E4-01_validation_report.pdf",
     "Module A precision/recall/refusal against held-out adjudicated "
     "adjacency; Module B model comparison and ablations.",
     "outputs/runs/run-20260922T104226Z/module_b/validation_report.json — raw program output"),
    ("E4", "Exhibit 20", "Acceptance Test Report", "E4-02_test_report.pdf",
     "Acceptance suites T01-T25 with observed outcomes.",
     "outputs/qa/junit.xml — pytest session transcript, 38 tests"),
    ("E4", "Exhibit 21", "Data Card", "E4-03_data_card.pdf",
     "Dataset formation, tables, data-quality handling and curation rules.",
     "outputs/reports/data_card_v2.0_20260922.md"),
    ("E4", "Exhibit 22", "Data Sample — Bills", "E4-04a_sample_bills.pdf",
     "De-identified bills table, first rows.",
     "outputs/runs/run-20260922T104226Z/data/bills.csv — first 25 rows"),
    ("E4", "Exhibit 23", "Data Sample — Events", "E4-04b_sample_events.pdf",
     "De-identified events table, first rows.",
     "outputs/runs/run-20260922T104226Z/data/events.csv — first 25 rows"),
    ("E4", "Exhibit 24", "Data Sample — Allocations", "E4-04c_sample_allocations.pdf",
     "De-identified allocations table, first rows.",
     "outputs/runs/run-20260922T104226Z/data/allocations.csv — first 25 rows"),
]


def _font(page):
    return page.insert_font(fontname="TNR", fontfile=TNR)


def _font_mono(page):
    return page.insert_font(fontname="MONO", fontfile=MONO)


def _text(page, x, y, text, size=10.0, color=(0, 0, 0), mono=False):
    page.insert_text((x, y), text, fontsize=size,
                     fontname="MONO" if mono else "TNR", color=color)


def _ctext(page, y, text, size=10.0, width=595.0):
    w = fitz.Font(fontfile=TNR).text_length(text, fontsize=size)
    page.insert_text(((width - w) / 2, y), text, fontsize=size, fontname="TNR")


def _wrap(text: str, max_w: float, size: float) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fitz.Font(fontfile=TNR).text_length(trial, fontsize=size) > max_w:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


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


def make_certification() -> fitz.Document:
    """Certification of true copies under 28 U.S.C. 1746."""
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _font_mono(p)
    _text(p, 56, 60, "CERTIFICATION OF TRUE COPIES", size=13)
    _text(p, 56, 90, "28 U.S.C. § 1746 — Unsworn Declaration", size=9, color=(0.3, 0.3, 0.3))
    y = 125
    paras = [
        "I, Yajie Xu, declare under penalty of perjury that the following is true and correct:",
        "",
        "1. The exhibits in this book are true and unaltered copies of the artifacts identified "
        "beside each exhibit number below, each rendered from the source path shown at the "
        "software repository and release tag referenced therein (lab_billing_research, v1.4.0, "
        "release candidate dated September 14, 2026).",
        "",
        "2. No content has been added to, removed from, or modified in any artifact except "
        "(a) redaction of identifying fields in the de-identified data samples, marked in the "
        "samples; (b) the removal of internal documentation keys noted on the validation "
        "report page; and (c) the header and footer markings identifying this exhibit book.",
        "",
        "3. The source of each artifact is stated on the label page immediately preceding it, "
        "and corresponds to the file at the repository commit shown in the repository exhibits.",
    ]
    for para in paras:
        if para == "":
            y += 10
            continue
        for ln in _wrap(para, 480, 9.5):
            _text(p, 56, y, ln, size=9.5)
            y += 14
        y += 2
    y += 16
    _text(p, 56, y, "Artifact index (24 exhibits):", size=10)
    y += 16
    for (sec, no, title, fn, desc, src) in EXHIBITS:
        _text(p, 56, y, f"{no} — {title}", size=8.5)
        y += 11
        _text(p, 72, y, src, size=7.5, color=(0.3, 0.3, 0.3), mono=True)
        y += 13
    y += 20
    _text(p, 56, y, "Executed on: _______________, 2026", size=9.5)
    y += 22
    _text(p, 56, y, "_________________________________", size=9.5)
    _text(p, 56, y + 12, "Yajie Xu", size=9.5)
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
        for (sec, no, title, fn, desc, src) in EXHIBITS:
            if sec != section or no not in page_map:
                continue
            _text(p, 70, y, f"{no}", size=10)
            _text(p, 130, y, title[:48], size=10)
            _text(p, 500, y, str(page_map[no]), size=10)
            y += 16
        y += 8
    _text(p, 56, 800, "Each exhibit is preceded by a label page stating its source.", size=8, color=(0.3, 0.3, 0.3))
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


def make_exhibit_label(no: str, title: str, desc: str, src: str) -> fitz.Document:
    """Label page: exhibit tab (top-left box) + title + one-line provenance,
    set in a bordered frame so it reads as a filing label, not narration."""
    d = fitz.open()
    p = d.new_page(width=595, height=842)
    _font(p)
    _font_mono(p)
    # exhibit tab, top-left
    p.draw_rect(fitz.Rect(56, 70, 200, 100), color=(0, 0, 0), width=1.2)
    _text(p, 66, 92, no.upper(), size=15)
    _text(p, 56, 120, title, size=12)
    # provenance line under the tab, in mono
    _text(p, 56, 150, "True copy of:", size=8.5, color=(0.3, 0.3, 0.3))
    y = 166
    for ln in _wrap(src, 460, 8):
        _text(p, 56, y, ln, size=8, mono=True)
        y += 12
    # description block, framed, lower area — clearly the drafter's framing
    p.draw_rect(fitz.Rect(56, 200, 539, 330), color=(0.45, 0.45, 0.45), width=0.8)
    _text(p, 66, 214, "Description (prepared for this exhibit book):", size=8, color=(0.35, 0.35, 0.35))
    y = 230
    for ln in _wrap(desc, 455, 9):
        _text(p, 66, y, ln, size=9)
        y += 13
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
    exhibit_ranges: dict[str, tuple[int, int]] = {}

    # cover (page 1)
    book.insert_pdf(make_cover())

    # certification (page 2, before the index)
    book.insert_pdf(make_certification())

    # assemble all exhibits; record where each exhibit's label page starts.
    current_section = None
    for (section, no, title, fn, desc, src) in EXHIBITS:
        src_path = os.path.join(FILING, fn)
        if not os.path.exists(src_path):
            print("MISSING", fn)
            continue
        if section != current_section:
            book.insert_pdf(make_divider(section))
            current_section = section
        part = fitz.open()
        part.insert_pdf(make_exhibit_label(no, title, desc, src))
        part.insert_pdf(normalize_to_a4(fitz.open(src_path)))
        start = book.page_count + 1
        book.insert_pdf(part)
        page_map[no] = start
        exhibit_ranges[no] = (start + 1, book.page_count)
        part.close()

    # insert master index right after the cover (becomes page 3)
    idx = make_index_page(page_map)
    book.insert_pdf(idx, start_at=2)

    # continuous Bates numbering + footer (final layout)
    for i in range(book.page_count):
        page = book[i]
        _font(page)
        _font_mono(page)
        y = page.rect.height - 24
        _text(page, 56, y, f"YAJIE-XU-E-{i + 1:04d}", size=7.5, color=(0.3, 0.3, 0.3))
        _text(page, 300, y, f"Exhibit Book · Page {i + 1}", size=8, color=(0.3, 0.3, 0.3))

    # bookmarks
    toc = []
    for (section, no, title, fn, desc, src) in EXHIBITS:
        if no in page_map:
            toc.append([1, f"{no} — {title}", page_map[no]])
    book.set_toc(toc)
    book.save(OUT, garbage=4, deflate=True)
    print(f"Exhibit book: {OUT} ({book.page_count} pages, {len(toc)} bookmarks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
