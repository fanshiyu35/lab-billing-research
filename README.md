# Lab Billing Research

Billing event reconstruction and payment-delay early-warning methods for clinical
laboratory settings. This repository contains the research tooling, synthetic
demonstration data, evaluation suites, and reports.

## Quick start

    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python -r requirements.lock.txt
    python scripts/run_demo.py --config configs/demo.json
    python -m pytest -q --junitxml outputs/qa/junit.xml
    streamlit run app/main.py --server.address 127.0.0.1

## Data status

- DEMO mode: synthetic data generated in-repo (seed 42). No real patient or
  billing data is contained in this repository.
- REAL-LOCAL mode: disabled by default; requires documented authorization.
  See governance/data_permissions.json.

## Layout

See CHANGELOG.md for version history and migration notes.
