# Lab Billing Research

Billing event reconstruction and payment-delay early-warning methods for clinical
laboratory settings. This repository contains the research tooling, the
de-identified data preparation pipeline, evaluation suites, and reports.

## Quick start

    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python -r requirements.lock.txt
    python scripts/run_pipeline.py --config configs/reference.json
    python -m pytest -q --junitxml outputs/qa/junit.xml
    streamlit run app/main.py --server.address 127.0.0.1

## Data

- The study uses de-identified billing event records from three participating
  clinical laboratory organizations (site tokens CPL / TRI / NDX). Adjudicated
  reference labels are held out from model inputs.
- Real-mode processing of identified data requires documented authorization
  (governance/data_permissions.json); it is disabled by default.

## Layout

See CHANGELOG.md for version history. Method documentation: outputs/reports/.
