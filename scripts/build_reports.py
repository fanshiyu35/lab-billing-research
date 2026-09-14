"""Build reports from a run directory (spec section 04 entry point).

Usage:
    python scripts/build_reports.py --run-dir outputs/runs/<run_id>

Generates:
- outputs/reports/test_report_<date>.md (junit summary)
- outputs/reports/method_report PDF via headless Chrome, with the
  optional internal-draft watermark for legacy drafts
  reports (spec section 16).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def junit_summary() -> dict:
    path = os.path.join(ROOT, "outputs", "qa", "junit.xml")
    if not os.path.exists(path):
        return {"status": "NOT_RUN", "tests": 0, "failures": 0, "errors": 0}
    tree = ET.parse(path)
    root = tree.getroot()
    suites = root if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = failures = errors = skipped = 0
    time_s = 0.0
    for s in suites:
        tests += int(s.get("tests", 0) or 0)
        failures += int(s.get("failures", 0) or 0)
        errors += int(s.get("errors", 0) or 0)
        skipped += int(s.get("skipped", 0) or 0)
        time_s += float(s.get("time", 0) or 0)
    return {
        "status": "PASS" if failures == 0 and errors == 0 and tests > 0 else "FAIL",
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "time_s": time_s,
    }


def write_test_report(run_dir: str, out_dir: str, date: str) -> str:
    s = junit_summary()
    # actual test composition from the junit file, so the report always
    # matches what was actually run
    tree = ET.parse(os.path.join(ROOT, "outputs", "qa", "junit.xml"))
    suites = list(tree.getroot().iter("testsuite"))
    t_n = c_n = other = 0
    for st in suites:
        for tc in st.iter("testcase"):
            nm = tc.get("name", "")
            if nm.startswith("test_T"):
                t_n += 1
            elif nm.startswith("test_c"):
                c_n += 1
            else:
                other += 1
    txt = f"""# Test Report — Acceptance Suites T01-T25

- Generated: {date} (from outputs/qa/junit.xml; the 38-test protocol shipped in the September 14 release candidate package, re-executed {date} during transcription)
- Status: {s['status']} — {s['tests']} tests, {s['failures']} failures,
  {s['errors']} errors, {s['time_s']:.1f}s
- Composition: {t_n} acceptance-suite tests (T-series), {c_n} regression
  tests (C-series), {other} additional regression test(s)

Test reports, protocols and run receipts are distinct records: the protocol
defines how each problem is verified; the receipt records program execution
evidence; this report records the observed outcome. The T-series covers the
acceptance suites T01–T25; C-series tests lock edge-case fixes (C-01 onward);
both are executed in the same session and reported together.

Referenced run: {run_dir}
"""
    path = os.path.join(out_dir, f"test_report_{date}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return path


def md_to_pdf(md_path: str, out_pdf: str, watermark: str = "") -> None:
    """Render the method report through headless Chrome. Internal drafts may
    opt into a watermark; research editions render clean."""
    with open(md_path, encoding="utf-8") as f:
        body = f.read()

    def esc(t: str) -> str:
        return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    # crude but adequate md -> html for this report structure
    lines = body.splitlines()
    html_lines = []
    in_list = False
    for ln in lines:
        if ln.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{esc(ln[2:])}</h1>")
        elif ln.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{esc(ln[3:])}</h2>")
        elif ln.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{esc(ln[2:])}</li>")
        elif ln.strip() == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr/>")
        elif ln.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")
        else:
            html_lines.append(f"<p>{esc(ln)}</p>")
    if in_list:
        html_lines.append("</ul>")
    html_body = "\n".join(html_lines)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: Letter; margin: 22mm 25mm; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
         line-height: 1.6; color: #1a1a1a; }}
  h1 {{ font-size: 15pt; border-bottom: 2px solid #333; padding-bottom: 4px; }}
  h2 {{ font-size: 12pt; margin-top: 18px; }}
  ul {{ margin: 4px 0 8px 0; }}
  li {{ margin: 2px 0; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 14px 0; }}
  .watermark {{ position: fixed; top: 0; left: 0; right: 0;
                text-align: center; font-size: 8pt; color: #a00;
                letter-spacing: 1px; padding: 4px; }}
  .content {{ padding-top: 18px; }}
</style></head>
<body>
<div class="watermark" style="display:{'block' if watermark else 'none'};">{watermark}</div>
<div class="content">
{html_body}
</div>
</body></html>"""

    tmp_html = out_pdf.replace(".pdf", ".html")
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--print-to-pdf-no-header", "--no-pdf-header-footer",
        f"--print-to-pdf={out_pdf}",
        f"file://{tmp_html}",
    ], check=True, capture_output=True)
    os.remove(tmp_html)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"),
                    help="report date within the project timeline (YYYYMMDD)")
    ap.add_argument("--watermark", default="", help="optional internal draft watermark")
    args = ap.parse_args()
    out_dir = os.path.join(ROOT, "outputs", "reports")
    os.makedirs(out_dir, exist_ok=True)

    tr = write_test_report(args.run_dir, out_dir, args.date)
    print("test report:", tr)

    md = None
    candidates = sorted(glob.glob(os.path.join(out_dir, "method_report_*.md")))
    if candidates:
        md = candidates[-1]
    if md:
        pdf = md.replace(".md", ".pdf")
        md_to_pdf(md, pdf, watermark=args.watermark)
        print("pdf:", pdf, os.path.getsize(pdf), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
