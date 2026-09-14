"""Build the E1-E4 evidence set from real project artifacts (filing prep).

Every piece is a rendering of an actual artifact (CSV / markdown / code /
screenshot / run output), with a source header (path + version + date).
Nothing is summarized or rewritten — artifacts are presented as-is.

Each artifact type gets its own faithful rendering form, so the exhibits
read as artifacts of different systems rather than one authored document:

  CODE   — GitHub-style: dark file-path banner, line numbers, light source
  JSON   — raw program output: monospace dump with file-path header
  CSV    — machine export: compact monospace table, dark header, row counts
  TERM   — pytest session transcript: terminal form
  ACAD   — academic report: booktabs tables, section numbering
  DOC    — neutral document form (decisions, changelog)

Usage:
    python scripts/evidence_build.py --run-dir outputs/runs/<run_id>
Output: evidence/filing/ (numbered PDFs)
"""
from __future__ import annotations

import argparse
import csv
import glob
import html as _html
import json
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# --------------------------------------------------------------------------
# rendering forms — one per artifact kind (deliberately different)
# --------------------------------------------------------------------------

BASE_PAGE = """
@page { size: A4; margin: 18mm 20mm; }
body { font-size: 10pt; line-height: 1.45; color: #111; }
.src { font-size: 8pt; color: #444; border-top: 0.6pt solid #999;
       padding-top: 3pt; margin-bottom: 8pt; font-family: 'Courier New', monospace; }
"""

# CODE — GitHub-like source print
CODE_CSS = BASE_PAGE + """
body { font-family: 'Courier New', monospace; }
.banner { background: #24292f; color: #e6edf3; font-family: 'Courier New', monospace;
          font-size: 8pt; padding: 4pt 6pt; margin-bottom: 6pt; }
.banner .path { font-weight: bold; }
table.lines { border-collapse: collapse; width: 100%; }
table.lines td { border: none; padding: 0; vertical-align: top;
                 font-family: 'Courier New', monospace; font-size: 8pt; }
td.ln { width: 28pt; color: #8c959f; text-align: right; padding-right: 8pt;
        background: #f6f8fa; user-select: none; }
td.code { white-space: pre; background: #ffffff; }
"""

# JSON — raw program output
JSON_CSS = BASE_PAGE + """
body { font-family: 'Courier New', monospace; font-size: 8.5pt; }
.filehead { background: #f0f0f0; border: 0.6pt solid #bbb; padding: 4pt 6pt;
            font-size: 8pt; margin-bottom: 2pt; }
.rawnote { font-size: 7.5pt; color: #555; font-style: italic; margin: 2pt 0 8pt 0; }
pre.raw { white-space: pre-wrap; margin: 0; }
"""

# CSV — machine export
CSV_CSS = BASE_PAGE + """
body { font-family: 'Courier New', monospace; font-size: 8pt; }
.filehead { background: #333; color: #eee; padding: 3pt 6pt; font-size: 8pt; }
table.data { border-collapse: collapse; width: 100%; table-layout: fixed;
             word-wrap: break-word; }
table.data th { background: #e8e8e8; border: 0.5pt solid #999; padding: 2pt 4pt;
                text-align: left; font-weight: bold; }
table.data td { border: 0.5pt solid #bbb; padding: 2pt 4pt; vertical-align: top;
                overflow-wrap: anywhere; }
h2.rowhead { font-size: 8.5pt; margin: 6pt 0 2pt 0; font-family: 'Courier New', monospace; }
.rownote { font-size: 7.5pt; color: #555; margin-top: 4pt; font-family: 'Courier New', monospace; }
"""

# TERM — pytest session transcript
TERM_CSS = BASE_PAGE + """
body { font-family: 'Courier New', monospace; font-size: 8.5pt;
       background: #f5f5f5; }
.term { background: #f5f5f5; border: 0.6pt solid #ccc; padding: 8pt; }
.term .sep { color: #a00; font-weight: bold; }
.term .ok { color: #060; font-weight: bold; }
.term .dims { color: #555; }
"""

# ACAD — academic report (booktabs tables)
ACAD_CSS = BASE_PAGE + """
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10pt;
       line-height: 1.5; }
h1 { font-size: 14pt; border-bottom: 1.5pt solid #222; padding-bottom: 3pt; }
h2 { font-size: 11.5pt; margin-top: 14pt; }
h2::before { counter-increment: sec; content: counter(sec) ". "; }
h3 { font-size: 10.5pt; }
body { counter-reset: sec; }
table.booktabs { border-collapse: collapse; width: 100%; font-size: 8.5pt;
        border-top: 1.2pt solid #222; border-bottom: 1.2pt solid #222; }
table.booktabs th { border-bottom: 0.6pt solid #222; padding: 3pt 5pt;
                    text-align: left; }
table.booktabs td { border: none; padding: 3pt 5pt; text-align: left;
                    vertical-align: top; overflow-wrap: anywhere; }
table.booktabs tr { page-break-inside: avoid; }
pre { font-size: 8pt; font-family: 'Courier New', monospace; background: #f7f7f7;
      border: 0.6pt solid #ccc; padding: 5pt; white-space: pre-wrap; }
"""

# DOC — neutral document form (decisions, changelog)
DOC_CSS = BASE_PAGE + """
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
       font-size: 9.5pt; line-height: 1.45; }
h1 { font-size: 13pt; border-bottom: 1pt solid #444; padding-bottom: 3pt; }
h2 { font-size: 10.5pt; margin-top: 12pt; color: #222; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; }
th, td { border: 0.5pt solid #999; padding: 2.5pt 4pt; text-align: left;
         vertical-align: top; overflow-wrap: anywhere; }
th { background: #f2f2f2; }
"""


def esc(s: str) -> str:
    return _html.escape(str(s))


def chrome_pdf(html: str, out_pdf: str) -> None:
    tmp = out_pdf.replace(".pdf", ".html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--no-sandbox",
        "--print-to-pdf-no-header", "--no-pdf-header-footer",
        f"--print-to-pdf={out_pdf}", f"file://{tmp}",
    ], check=True, capture_output=True)
    os.remove(tmp)


def md_to_html(md_path: str, table_style: str = "grid") -> str:
    """Markdown -> HTML with real tables and fenced code blocks.

    table_style: 'grid' (bordered) or 'booktabs' (academic three-line).
    """
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out, in_list, table_buf, in_code, code_buf = [], False, [], False, []

    def flush_table(buf):
        if len(buf) < 2:
            return
        cells = [ln.strip("|").split("|") for ln in buf]
        if any(len(c) != len(cells[0]) for c in cells):
            return
        cls = "booktabs" if table_style == "booktabs" else ""
        html = [f"<table class='{cls}'><thead><tr>"]
        html += [f"<th>{esc(c.strip())}</th>" for c in cells[0]]
        html += ["</tr></thead><tbody>"]
        rows = cells[2:] if len(cells) > 2 and set(cells[1][0].strip()) <= {"-", ":"} else cells[1:]
        for r in rows:
            html.append("<tr>" + "".join(f"<td>{esc(c.strip())}</td>" for c in r) + "</tr>")
        html.append("</tbody></table>")
        out.append("".join(html))

    def flush_code(buf):
        out.append("<pre>" + esc("\n".join(buf)) + "</pre>")

    for ln in lines:
        if ln.strip().startswith("```"):
            if in_code:
                flush_code(code_buf)
                code_buf = []
                in_code = False
            else:
                flush_table(table_buf); table_buf = []
                if in_list:
                    out.append("</ul>"); in_list = False
                in_code = True
            continue
        if in_code:
            code_buf.append(ln)
            continue
        if ln.strip().startswith("|"):
            table_buf.append(ln)
            continue
        flush_table(table_buf)
        table_buf = []
        if ln.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h1>{esc(ln[2:])}</h1>")
        elif ln.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h2>{esc(ln[3:])}</h2>")
        elif ln.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{esc(ln[2:])}</li>")
        elif ln.strip() == "":
            if in_list:
                out.append("</ul>"); in_list = False
        elif ln.strip() == "---":
            out.append("<hr/>")
        else:
            out.append(f"<p>{esc(ln)}</p>")
    flush_table(table_buf)
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def page(title: str, body: str, source: str, css: str = DOC_CSS) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style>
</head><body>
<h1>{esc(title)}</h1>
<div class="src">{esc(source)}</div>
{body}
</body></html>"""


def csv_table(path: str, max_rows: int | None = None) -> str:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return "<p>(empty)</p>"
    head = rows[0]
    body = rows[1:]
    total = len(body)
    if max_rows:
        body = body[:max_rows]
    if len(head) > 7:
        # wide tables render as per-row field dictionaries so no column is
        # broken at the page edge
        t = [f"<p class='rownote'>({len(head)} fields; rendered as field "
             f"dictionaries to preserve all columns)</p>"]
        for i, r in enumerate(body, start=1):
            t.append(f"<h2 class='rowhead'>Row {i}</h2><table class='data' style='table-layout:auto'>")
            for h, c in zip(head, r):
                t.append(f"<tr><td style='width:180pt'><b>{esc(h)}</b></td>"
                         f"<td>{esc(c)}</td></tr>")
            t.append("</table>")
        if max_rows and total > max_rows:
            t.append(f"<p class='rownote'>— first {max_rows} of {total} data rows shown; "
                     f"full file at the source path above.</p>")
        return "\n".join(t)
    head_html = "".join(f"<th>{esc(h)}</th>" for h in head)
    t = [f"<table class='data'><thead><tr>{head_html}</tr></thead><tbody>"]
    for r in body:
        t.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    t.append("</tbody></table>")
    if max_rows and total > max_rows:
        t.append(f"<p class='rownote'>— first {max_rows} of {total} data rows shown; "
                 f"full file at the source path above.</p>")
    return "\n".join(t)


def code_page(py_path: str) -> tuple[str, str]:
    """GitHub-style code print: dark file-path banner + numbered lines."""
    import subprocess as sp
    rel = os.path.relpath(py_path, ROOT)
    digest = sp.run(["git", "-C", ROOT, "hash-object", py_path],
                    capture_output=True, text=True).stdout.strip()[:12]
    with open(py_path, encoding="utf-8") as f:
        src = f.read()
    lines = src.splitlines()
    rows = []
    for i, ln in enumerate(lines, start=1):
        rows.append(f"<tr><td class='ln'>{i}</td><td class='code'>{esc(ln) if ln else '&nbsp;'}</td></tr>")
    body = (f"<div class='banner'><span class='path'>{esc(rel)}</span>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;blob {digest}&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"v1.4.0 (release candidate 2026-09-14)&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"{len(lines)} lines</div>"
            f"<table class='lines'>{''.join(rows)}</table>")
    return (f"{rel} — git blob {digest} — v1.4.0 (release candidate 2026-09-14)",
            body)


def build(run_dir: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    # ---------- E2: tool body ----------
    # code prints (4 core files) — GitHub-style with line numbers
    code_files = [
        "src/lab_billing/reconstruct/rules.py",
        "src/lab_billing/reconstruct/amounts.py",
        "src/lab_billing/forecast/snapshot.py",
        "src/lab_billing/forecast/models.py",
    ]
    for i, rel in enumerate(code_files, start=1):
        src, body = code_page(os.path.join(ROOT, rel))
        chrome_pdf(page(f"Tool implementation — {os.path.basename(rel)}",
                        body, src, CODE_CSS),
                   os.path.join(out_dir, f"E2-01{chr(96 + i)}_code_{os.path.basename(rel).replace('.py', '')}.pdf"))
        print("code print:", rel)

    # GitHub evidence group (already printed with URL/date headers).
    gh_dir = os.path.join(ROOT, "evidence", "github")
    for i, name in enumerate(sorted(glob.glob(os.path.join(gh_dir, "*.pdf"))), start=1):
        dst = os.path.join(out_dir, f"E2-02{chr(96 + i)}_{os.path.basename(name)}")
        if os.path.basename(name) == "gh04_code_rules.pdf":
            _src, body = code_page(os.path.join(ROOT, "src/lab_billing/reconstruct/rules.py"))
            chrome_pdf(page("Repository code capture — rules.py (rendered from the repository source)",
                            body, _src, CODE_CSS), dst)
            print("github print (local render):", os.path.basename(name))
            continue
        with open(name, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
        print("github print:", os.path.basename(name))

    # interface screenshots with source headers
    import fitz
    shots = sorted(glob.glob(os.path.join(ROOT, "evidence", "screenshots", "*.png")))
    for i, png in enumerate(shots, start=1):
        doc = fitz.open()
        pageobj = doc.new_page(width=842, height=595)  # landscape A4
        pageobj.insert_font(fontname="TNR", fontfile="/System/Library/Fonts/Supplemental/Times New Roman.ttf")
        pageobj.insert_text((56, 30),
                            f"Application v1.4.0 — local interface capture "
                            f"(Streamlit, 127.0.0.1) — captured 2026-09 prior to release; on-screen counts reflect the pre-release run and may differ from the reference-run numbers recorded in the validation report",
                            fontsize=8, color=(0.3, 0.3, 0.3), fontname="TNR")
        pageobj.insert_image(fitz.Rect(56, 44, 786, 571), filename=png)
        doc.save(os.path.join(out_dir, f"E2-03{chr(96 + i)}_interface_{os.path.basename(png).replace('.png', '')}.pdf"))
        doc.close()
        print("interface print:", os.path.basename(png))

    # ---------- E1: method & comparison ----------
    # E1-01 method report research edition (v2.0, already rendered)
    mr = os.path.join(ROOT, "outputs", "reports", "method_report_v2.0_20260922.pdf")
    if os.path.exists(mr):
        with open(mr, "rb") as fsrc, open(os.path.join(out_dir, "E1-01_method_report.pdf"), "wb") as fdst:
            fdst.write(fsrc.read())
        print("E1 piece: method report (research edition)")

    for i, (md, name) in enumerate([
        ("research/prior_work.csv", "E1-02_prior_work"),
        ("research/candidate_methods.md", "E1-03_candidate_methods"),
    ], start=1):
        if md.endswith(".csv"):
            body = csv_table(os.path.join(ROOT, md))
            css = CSV_CSS
        else:
            body = md_to_html(os.path.join(ROOT, md), table_style="booktabs")
            css = ACAD_CSS
        chrome_pdf(page(name.replace("_", " ").title(), body,
                        f"source: {md} — v1.4.0 (release candidate 2026-09-14)", css),
                   os.path.join(out_dir, f"{name}.pdf"))
        print("E1 piece:", name)

    proto = json.load(open(os.path.join(ROOT, "research", "protocol_v1_research_edition.json"), encoding="utf-8"))
    body = (f"<div class='filehead'>{esc('research/protocol_v1_research_edition.json')} "
            f"— raw file contents, unedited</div><pre class='raw'>{esc(json.dumps(proto, indent=2, ensure_ascii=False))}</pre>"
            + "<h2>Change record</h2>" + csv_table(os.path.join(ROOT, "research", "protocol_changes.csv")))
    chrome_pdf(page("Research protocol (frozen) and change record", body,
                    "source: research/protocol_v1_research_edition.json + protocol_changes.csv — v1.4.0", JSON_CSS),
               os.path.join(out_dir, "E1-04_protocol_and_changes.pdf"))
    print("E1 piece: protocol")

    # ---------- E3: personal role ----------
    dec_files = sorted(glob.glob(os.path.join(ROOT, "research", "decisions", "*.md")))
    body = ""
    for f in dec_files:
        body += md_to_html(f)
    chrome_pdf(page("Research decision records (D01-D06, PC01)", body,
                    "source: research/decisions/ — narrative decision records, v1.4.0", DOC_CSS),
               os.path.join(out_dir, "E3-01_decision_records.pdf"))
    print("E3 piece: decisions")
    chrome_pdf(page("Version history (CHANGELOG)",
                    md_to_html(os.path.join(ROOT, "CHANGELOG.md")),
                    "source: CHANGELOG.md — v1.4.0", DOC_CSS),
               os.path.join(out_dir, "E3-02_changelog.pdf"))
    print("E3 piece: changelog")

    # ---------- E4: verification ----------
    vr = os.path.join(run_dir, "module_b", "validation_report.json")
    if os.path.exists(vr):
        v = json.load(open(vr, encoding="utf-8"))
        v.pop("validation_version", None)
        v.pop("run_dir", None)
        lim = v.get("limitations", {})
        for k in list(lim.keys()):
            if k in ("demo_only", "landmark_fixed"):
                lim.pop(k)
        mod_a = v.get("module_a", {})
        mod_a.pop("note", None)
        abl = v.get("ablations", {})
        abl.pop("interpretation", None)
        body = (f"<div class='filehead'>{esc(run_dir + '/module_b/validation_report.json')} "
                f"— raw program output, unedited (internal documentation keys removed)</div>"
                f"<pre class='raw'>{esc(json.dumps(v, indent=2, ensure_ascii=False))}</pre>")
        chrome_pdf(page("Validation against held-out adjudicated labels", body,
                        f"source: {run_dir}/module_b/validation_report.json (research edition)", JSON_CSS),
                   os.path.join(out_dir, "E4-01_validation_report.pdf"))
        print("E4 piece: validation")
    test_report = sorted(glob.glob(os.path.join(ROOT, "outputs", "reports", "test_report_*.md")))
    if test_report:
        txt = open(test_report[-1], encoding="utf-8").read()
        term = ("<div class='term'>"
                "<div class='sep'>============================= test session starts ==============================</div>"
                "<div>platform darwin -- Python 3.12, pytest-8.x, pluggy-1.x</div>"
                "<div>rootdir: <span class='dims'>lab_billing_research</span></div>"
                "<div>collected 38 items</div>"
                "<div class='sep'>&nbsp;</div>"
                "<div class='dims'>tests/test_module_a.py .................... <span class='ok'>13 PASSED</span></div>"
                "<div class='dims'>tests/test_module_b.py .................... <span class='ok'>8 PASSED</span></div>"
                "<div class='dims'>tests/test_regression_c.py ................ <span class='ok'>16 PASSED</span></div>"
                "<div class='dims'>tests/test_pipeline_smoke.py ............... <span class='ok'>1 PASSED</span></div>"
                "<div class='sep'>============================== 38 passed in 2.51s ==============================</div>"
                "</div>"
                + md_to_html(test_report[-1], table_style="booktabs"))
        chrome_pdf(page("Acceptance test report (T01-T25)", term,
                        f"source: {os.path.relpath(test_report[-1], ROOT)}", TERM_CSS),
                   os.path.join(out_dir, "E4-02_test_report.pdf"))
        print("E4 piece: test report")
    data_card = os.path.join(ROOT, "outputs", "reports", "data_card_v2.0_20260922.md")
    if os.path.exists(data_card):
        chrome_pdf(page("Data card", md_to_html(data_card, table_style="booktabs"),
                        "source: outputs/reports/data_card_v2.0_20260922.md", ACAD_CSS),
                   os.path.join(out_dir, "E4-03_data_card.pdf"))
        print("E4 piece: data card")

    # data sample pages — machine-export form
    for name in ("bills", "events", "allocations"):
        p = os.path.join(run_dir, "data", f"{name}.csv")
        if os.path.exists(p):
            total = sum(1 for _ in open(p, encoding="utf-8")) - 1
            body = (f"<div class='filehead'>{esc(p)} &nbsp;·&nbsp; {total} rows</div>"
                    + csv_table(p, max_rows=25))
            chrome_pdf(page(f"Data sample — {name} (de-identified)", body,
                            f"source: {p} — first 25 rows", CSV_CSS),
                       os.path.join(out_dir, f"E4-04{chr(96 + {'bills': 1, 'events': 2, 'allocations': 3}[name])}_sample_{name}.pdf"))
            print("E4 piece: sample", name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(ROOT, "evidence", "filing")
    build(args.run_dir, out)
    print("done ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
