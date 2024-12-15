"""Run module B (forecast) on a module A output directory.

Usage:
    python scripts/run_forecast.py --module-a outputs/runs/<run_id>/module_a \
        --out outputs/runs/<run_id>/module_b
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lab_billing.forecast import ForecastPipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module-a", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="forecast-run")
    args = ap.parse_args()

    pipe = ForecastPipeline(run_id=args.run_id)
    report = pipe.run(args.module_a, args.out)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
