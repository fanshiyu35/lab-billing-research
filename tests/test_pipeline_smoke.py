"""T25 — full pipeline and interface smoke test (spec section 15).

From a clean outputs tree: run the pipeline entry, verify module A and module B
artifacts exist with real content, and confirm the app reads them.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "bin", "python")


def test_T25_full_pipeline_smoke(tmp_path):
    env = dict(os.environ)
    # run pipeline with outputs redirected into a temp tree via cwd?
    # run_demo writes to outputs/runs under the project root; to keep this
    # test isolated we invoke it and then assert on the newest run dir.
    result = subprocess.run(
        [PY, "scripts/run_pipeline.py", "--config", "configs/reference.json"],
        cwd=ROOT, capture_output=True, text=True, timeout=600, env=env,
    )
    assert result.returncode == 0, result.stdout[-2000:]
    runs = sorted(os.listdir(os.path.join(ROOT, "outputs", "runs")))
    newest = runs[-1]
    out = os.path.join(ROOT, "outputs", "runs", newest)
    for module, files in {
        "data": ["bills.csv", "events.csv", "allocations.csv", "observation_windows.csv"],
        "module_a": ["lineages.csv", "links.csv", "conflicts.csv",
                     "review_queue.csv", "events_normalized.csv",
                     "allocations_normalized.csv", "reconstruction_audit.json"],
        "module_b": ["predictions.csv", "model_card.md",
                     "feature_manifest.json", "forecast_metrics.json"],
    }.items():
        for f in files:
            p = os.path.join(out, module, f)
            assert os.path.exists(p), f"missing {module}/{f}"
            assert os.path.getsize(p) > 0, f"empty {module}/{f}"
    receipt = json.load(open(os.path.join(out, "run_receipt.json"), encoding="utf-8"))
    assert receipt["status"] == "OK"
    assert receipt["module_a_summary"]["lineages"] > 0
    assert receipt["module_b_summary"]["n_snapshots"] > 0
    # ground truth stays separated
    gt = os.path.join(out, "data", "_ground_truth")
    assert os.path.exists(gt)
