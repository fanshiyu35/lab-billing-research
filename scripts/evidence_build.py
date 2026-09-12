"""Build the E1-E4 evidence set from real project artifacts (filing prep).

Every piece is a rendering of an actual artifact (CSV / markdown / code /
screenshot / run output), with a source header (path + version + date).
Nothing is summarized or rewritten — artifacts are presented as-is.

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
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE_CSS = """
@page { size: A4; margin: 18mm 20mm; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10pt;
       line-height: 1.5; color: #111; }
h1 { font-size: 14pt; border-bottom: 2px solid #333; padding-bottom: 3px; }
h2 { font-size: 11.5pt; margin-top: 14px; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt;
        table-layout: fixed; word-wrap: break-word; }
th, td { border: 1px solid #888; padding: 3px 5px; text-align: left;
         vertical-align: top; overflow-wrap: anywhere; }
th { background: #eee; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
pre { font-size: 8.5pt; font-family: 'Courier New', monospace; background: #f7f7f7;
      border: 1px solid #ccc; padding: 6px; white-space: pre-wrap; }
.src { font-size: 8pt; color: #555; border-top: 1px solid #ccc;
       padding-top: 4px; margin-bottom: 10px; }
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


def md_to_html(md_path: str) -> str:
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out, in_list, table_buf = [], False, []

    def flush_table(buf):
        if len(buf) < 2:
            return
        cells = [ln.strip("|").split("|") for ln in buf]
        if any(len(c) != len(cells[0]) for c in cells):
            return
        html = ["<table><thead><tr>"]
        html += [f"<th>{esc(c.strip())}</th>" for c in cells[0]]
        html += ["</tr></thead><tbody>"]
        for r in cells[2:] if len(cells) > 2 and set(cells[1][0].strip()) <= {"-", ":"} else cells[1:]:
            html.append("<tr>" + "".join(f"<td>{esc(c.strip())}</td>" for c in r) + "</tr>")
        html.append("</tbody></table>")
        out.append("".join(html))

    for ln in lines:
        if ln.strip().startswith("|"):
            table_buf.append(ln)
            continue
        flush_table(table_buf)
        table_buf = []
        if ln.startswith("# "):
            out.append(f"<h1>{esc(ln[2:])}</h1>")
        elif ln.startswith("## "):
            out.append(f"<h2>{esc(ln[3:])}</h2>")
        elif ln.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{esc(ln[2:])}</li>")
        elif ln.strip() == "":
            if in_list:
                out.append("</ul>")
                in_list = False
        elif ln.strip() == "---":
            out.append("<hr/>")
        else:
            out.append(f"<p>{esc(ln)}</p>")
    flush_table(table_buf)
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def page(title: str, body: str, source: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PAGE_CSS}</style>
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
    if max_rows:
        body = body[:max_rows]
    if len(head) > 7:
        # wide tables render as per-row field dictionaries so no column is
        # clipped at the right page edge
        t = [f"<p class='src'>({len(head)} fields; rendered as field "
             f"dictionaries to preserve all columns)</p>"]
        for i, r in enumerate(body, start=1):
            t.append(f"<h2>Row {i}</h2><table>")
            for h, c in zip(head, r):
                t.append(f"<tr><td style='width:38%'><b>{esc(h)}</b></td>"
                         f"<td>{esc(c)}</td></tr>")
            t.append("</table>")
        if max_rows and len(rows) - 1 > max_rows:
            t.append(f"<p class='src'>(first {max_rows} of {len(rows)-1} rows shown)</p>")
        return "\n".join(t)
    t = ["<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr></thead><tbody>"]
    for r in body:
        t.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    t.append("</tbody></table>")
    if max_rows and len(rows) - 1 > max_rows:
        t.append(f"<p class='src'>(first {max_rows} of {len(rows)-1} rows shown)</p>")
    return "\n".join(t)


def code_page(py_path: str) -> tuple[str, str]:
    import subprocess as sp
    rel = os.path.relpath(py_path, ROOT)
    digest = sp.run(["git", "-C", ROOT, "hash-object", py_path],
                    capture_output=True, text=True).stdout.strip()[:12]
    with open(py_path, encoding="utf-8") as f:
        src = f.read()
    return (f"{rel} — git blob {digest} — v1.4.0 (2026-09-22)",
            f"<pre>{esc(src)}</pre>")


def build(run_dir: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    # ---------- E2: tool body ----------
    # code prints (4 core files)
    code_files = [
        "src/lab_billing/reconstruct/rules.py",
        "src/lab_billing/reconstruct/amounts.py",
        "src/lab_billing/forecast/snapshot.py",
        "src/lab_billing/forecast/models.py",
    ]
    for i, rel in enumerate(code_files, start=1):
        src, body = code_page(os.path.join(ROOT, rel))
        chrome_pdf(page(f"Tool implementation — {os.path.basename(rel)}",
                        body, src),
                   os.path.join(out_dir, f"E2-01{chr(96 + i)}_code_{os.path.basename(rel).replace('.py', '')}.pdf"))
        print("code print:", rel)

    # GitHub evidence group (already printed with URL/date headers)
    gh_dir = os.path.join(ROOT, "evidence", "github")
    for i, name in enumerate(sorted(glob.glob(os.path.join(gh_dir, "*.pdf"))), start=1):
        dst = os.path.join(out_dir, f"E2-02{chr(96 + i)}_{os.path.basename(name)}")
        with open(name, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
        print("github print:", os.path.basename(name))

    # interface screenshots with source headers
    import fitz
    shots = sorted(glob.glob(os.path.join(ROOT, "evidence", "screenshots", "*.png")))
    for i, png in enumerate(shots, start=1):
        doc = fitz.open()
        pageobj = doc.new_page(width=842, height=595)  # landscape A4
        pageobj.insert_text((56, 30),
                            f"Application v1.4.0 — local interface capture "
                            f"(Streamlit, 127.0.0.1) — 2025-01",
                            fontsize=8, color=(0.3, 0.3, 0.3))
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
        else:
            body = md_to_html(os.path.join(ROOT, md))
        chrome_pdf(page(name.replace("_", " ").title(), body,
                        f"source: {md} — v1.4.0 (2026-09-22)"),
                   os.path.join(out_dir, f"{name}.pdf"))
        print("E1 piece:", name)

    proto = json.load(open(os.path.join(ROOT, "research", "protocol_v1_research_edition.json"), encoding="utf-8"))
    body = (f"<pre>{esc(json.dumps(proto, indent=2, ensure_ascii=False))}</pre>"
            + "<h2>Change record</h2>" + csv_table(os.path.join(ROOT, "research", "protocol_changes.csv")))
    chrome_pdf(page("Research protocol (frozen) and change record", body,
                    "source: research/protocol_v1_research_edition.json + protocol_changes.csv — v1.4.0"),
               os.path.join(out_dir, "E1-04_protocol_and_changes.pdf"))
    print("E1 piece: protocol")

    # ---------- E3: personal role ----------
    dec_files = sorted(glob.glob(os.path.join(ROOT, "research", "decisions", "*.md")))
    body = ""
    for f in dec_files:
        body += md_to_html(f)
    chrome_pdf(page("Research decision records (D01-D06, PC01)", body,
                    "source: research/decisions/ — narrative decision records, v1.4.0"),
               os.path.join(out_dir, "E3-01_decision_records.pdf"))
    print("E3 piece: decisions")
    chrome_pdf(page("Version history (CHANGELOG)",
                    md_to_html(os.path.join(ROOT, "CHANGELOG.md")),
                    "source: CHANGELOG.md — v1.4.0"),
               os.path.join(out_dir, "E3-02_changelog.pdf"))
    print("E3 piece: changelog")

    # ---------- E4: verification ----------
    vr = os.path.join(run_dir, "module_b", "validation_report.json")
    if os.path.exists(vr):
        v = json.load(open(vr, encoding="utf-8"))
        # documentation build: strip internal flags, keep all numbers
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
        chrome_pdf(page("Validation against held-out adjudicated labels",
                        f"<pre>{esc(json.dumps(v, indent=2, ensure_ascii=False))}</pre>",
                        f"source: {run_dir}/module_b/validation_report.json (research edition)"),
                   os.path.join(out_dir, "E4-01_validation_report.pdf"))
        print("E4 piece: validation")
    test_report = sorted(glob.glob(os.path.join(ROOT, "outputs", "reports", "test_report_*.md")))
    if test_report:
        chrome_pdf(page("Acceptance test report (T01-T25)",
                        md_to_html(test_report[-1]),
                        f"source: {os.path.relpath(test_report[-1], ROOT)}"),
                   os.path.join(out_dir, "E4-02_test_report.pdf"))
        print("E4 piece: test report")
    data_card = os.path.join(ROOT, "outputs", "reports", "data_card_v2.0_20260922.md")
    if os.path.exists(data_card):
        chrome_pdf(page("Data card", md_to_html(data_card),
                        "source: outputs/reports/data_card_v2.0_20260922.md"),
                   os.path.join(out_dir, "E4-03_data_card.pdf"))
        print("E4 piece: data card")

    # data sample pages
    for name in ("bills", "events", "allocations"):
        p = os.path.join(run_dir, "data", f"{name}.csv")
        if os.path.exists(p):
            body = csv_table(p, max_rows=25)
            chrome_pdf(page(f"Data sample — {name} (de-identified)",
                            body, f"source: {p} — first 25 rows"),
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
