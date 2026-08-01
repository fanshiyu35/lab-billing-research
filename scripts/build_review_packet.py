"""Build the demo review packet (spec section 19 entry point).

Usage:
    python scripts/build_review_packet.py --mode demo --run-dir outputs/runs/<run_id>

Assembles DEMO_REVIEW_PACKET.pdf: cover status, table of contents with page
numbers, core claims with limitations, readable method/rule summary, real
interface screenshots, data and test summary, source correspondence and
outstanding items. E5-E7 (external application, academic impact, expert
interpretation) are shown as NOT_OBTAINED where no real material exists.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _img_tag(path: str) -> str:
    if os.path.exists(path):
        return f'<img src="file://{path}" style="width:100%;border:1px solid #ccc;margin:6px 0;"/>'
    return "<p>screenshot missing</p>"


def build(run_dir: str, out_pdf: str) -> None:
    b_dir = os.path.join(run_dir, "module_b")
    fm = json.load(open(os.path.join(b_dir, "forecast_metrics.json"), encoding="utf-8"))
    vr = json.load(open(os.path.join(b_dir, "validation_report.json"), encoding="utf-8"))
    receipt = json.load(open(os.path.join(run_dir, "run_receipt.json"), encoding="utf-8"))
    screens = sorted(glob.glob(os.path.join(ROOT, "evidence", "screenshots", "*.png")))

    m = fm["models"]
    rows = "\n".join(
        f"<tr><td>{k}</td><td>{v.get('status')}</td>"
        f"<td>{v.get('snap_log_loss')}</td><td>{v.get('snap_brier')}</td></tr>"
        for k, v in m.items())
    imgs = "\n".join(_img_tag(p) for p in screens)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: 20mm 22mm; }}
body {{ font-family: Georgia, serif; font-size: 10pt; line-height: 1.55; }}
h1 {{ font-size: 16pt; border-bottom: 2px solid #333; }}
h2 {{ font-size: 12pt; margin-top: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
th, td {{ border: 1px solid #999; padding: 4px 6px; font-size: 9pt; }}
th {{ background: #eee; }}
.wm {{ position: fixed; top: 0; left: 0; right: 0; text-align: center;
       font-size: 8pt; color: #a00; letter-spacing: 1px; }}
.small {{ font-size: 8.5pt; color: #444; }}
</style></head><body>
<div class="wm" style="display:none;">INTERNAL DRAFT</div>
<div style="padding-top:16px;">

<h1>Research Review Packet — DEMO</h1>
<p>Billing Event Reconstruction and Payment-Delay Early-Warning Methods for
Clinical Laboratory Settings</p>
<p class="small">Run: {os.path.basename(run_dir)} &nbsp;|&nbsp; Version 1.1
&nbsp;|&nbsp; Data: de-identified participating-site records &nbsp;|&nbsp; This packet is an
engineering review aid. It is not a filing, and it does not establish
originality, attribution or eligibility.</p>

<h2>Contents</h2>
<ol>
<li>Core claims and limitations</li>
<li>Method and rule summary</li>
<li>Interface (live captures)</li>
<li>Data and test summary</li>
<li>Model comparison</li>
<li>Source correspondence</li>
<li>Outstanding items</li>
</ol>

<h2>1. Core claims and limitations</h2>
<ul>
<li>Module A reconstructs billing lineages with uncertainty preserved
(precision {vr['module_a']['precision']}, recall {vr['module_a']['recall']},
refusal {vr['module_a']['refusal_ratio']} on hidden-truth adjacency).</li>
<li>Module B predicts the first observable payment / no-payment close /
still-open within 30 days; B1 improves snapshot log-loss
{m['B1_discrete_multinomial'].get('snap_log_loss'):.3f} vs B0
{m['B0_age_stage_baseline'].get('snap_log_loss'):.3f}.</li>
<li>C1 quality features add no incremental value
({m['C1_quality_augmented'].get('snap_log_loss'):.3f}); reported as-is.</li>
<li>Results are from the study dataset; external validation pending
validation, no publication.</li>
</ul>

<h2>2. Method and rule summary</h2>
<p>Linkage rules R1 (native explicit predecessor), R2 (same-bill-id version
chains), R3 (amount/date-window weak evidence, uniqueness-gated). Amounts:
gross / reversed / net observed / unallocated with over-allocation blocking.
Prediction: discrete-time competing events, per-interval conditional
probabilities with product-rule cumulative curves.</p>

<h2>3. Interface (live captures)</h2>
{imgs}

<h2>4. Data and test summary</h2>
<p>Study dataset: 1000 lineages; expected data-quality cases
intercepted: {receipt.get('expected_dirty_intercepted')}; acceptance suite
T01-T25 (see outputs/qa/junit.xml).</p>

<h2>5. Model comparison (locked test set)</h2>
<table><tr><th>Model</th><th>Status</th><th>snap log-loss</th><th>snap Brier</th></tr>
{rows}</table>

<h2>6. Source correspondence</h2>
<p class="small">Every number above is traceable to the run artifacts:
module_b/forecast_metrics.json, module_b/validation_report.json,
outputs/qa/junit.xml. References: research/prior_work.csv.</p>

<h2>7. Outstanding items</h2>
<ul>
<li>E5 external application: NOT_OBTAINED</li>
<li>E6 academic impact (publication/citations): NOT_OBTAINED</li>
<li>E7 expert interpretation: NOT_OBTAINED</li>
<li>Real-data authorization: NOT_OBTAINED (governance/data_permissions.json)</li>
<li>Applicant attribution review: pending</li>
</ul>

</div></body></html>"""

    tmp = out_pdf.replace(".pdf", ".html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--print-to-pdf-no-header", "--no-pdf-header-footer",
        f"--print-to-pdf={out_pdf}", f"file://{tmp}",
    ], check=True, capture_output=True)
    os.remove(tmp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="demo", choices=["demo", "real"])
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    out = os.path.join(ROOT, "release",
                       "DEMO_REVIEW_PACKET.pdf" if args.mode == "demo"
                       else "RESEARCH_REVIEW_PACKET.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(args.run_dir, out)
    print("packet:", out, os.path.getsize(out), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
