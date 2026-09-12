"""Local Streamlit interface for the lab billing research tool (spec 14).

Pages: project/data status, data validation, event reconstruction,
manual review, delay early-warning, test comparison, export.
Binds to 127.0.0.1 only. Reads actual run outputs; never writes back to
production systems. All sensitive rows stay out of exports.
"""
from __future__ import annotations

import csv
import glob
import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Lab Billing Research", layout="wide")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@st.cache_data(show_spinner=False)
def list_runs() -> list[str]:
    runs = sorted(glob.glob(os.path.join(ROOT, "outputs", "runs", "run-*")))
    return [os.path.basename(r) for r in runs][-20:]


@st.cache_data(show_spinner=False)
def load_csv(run: str, module: str, name: str) -> pd.DataFrame:
    path = os.path.join(ROOT, "outputs", "runs", run, module, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def main() -> None:
    runs = list_runs()
    if not runs:
        st.error("No runs found. Execute scripts/run_pipeline.py first.")
        return
    run = st.sidebar.selectbox("Run", runs, index=len(runs) - 1)
    data_dir = os.path.join(ROOT, "outputs", "runs", run, "data")
    manifest = {}
    mp = os.path.join(data_dir, "data_manifest.json")
    if os.path.exists(mp):
        manifest = json.load(open(mp, encoding="utf-8"))

    page = st.sidebar.radio(
        "Page",
        ["Project / data status", "Data validation", "Event reconstruction",
         "Manual review", "Delay early-warning", "Test comparison", "Export"],
    )

    if page == "Project / data status":
        st.header("Project and data status")
        st.write(f"**Run ID:** {run}")
        st.write("**Data:** de-identified billing event records from three "
                 "participating clinical laboratory organizations "
                 "(site tokens CPL / TRI / NDX)")
        st.write(f"**Lineages:** {manifest.get('n_lineages', '?')}")
        st.write(f"**Data window:** {manifest.get('business_start', '?')} "
                 f"-> {manifest.get('as_of', '?')}")
        with open(os.path.join(ROOT, "governance", "data_permissions.json"),
                  encoding="utf-8") as f:
            perm = json.load(f)
        st.subheader("Authorization status")
        st.write(f"identified-data processing: {perm.get('real_data_enabled')}")
        st.write(f"status: {perm.get('status')}")
        st.caption("Processing of identified data requires documented "
                   "authorization and remains disabled.")

    elif page == "Data validation":
        st.header("Data validation")
        bills = load_csv(run, "data", "bills.csv")
        events = load_csv(run, "data", "events.csv")
        st.metric("Bill rows", len(bills))
        st.metric("Event rows", len(events))
        st.metric("Allocation rows", len(load_csv(run, "data", "allocations.csv")))
        if not bills.empty:
            st.subheader("Bills (first 50)")
            st.dataframe(bills.head(50))
        st.caption("Invalid rows were isolated by the schema validator and are "
                   "excluded from reconstruction inputs; originals are retained.")

    elif page == "Event reconstruction":
        st.header("Event reconstruction")
        lineages = load_csv(run, "module_a", "lineages.csv")
        links = load_csv(run, "module_a", "links.csv")
        conflicts = load_csv(run, "module_a", "conflicts.csv")
        st.metric("Lineages", len(lineages))
        st.metric("Links", len(links))
        st.metric("Conflicts", len(conflicts))
        if not lineages.empty:
            selected = st.selectbox("Lineage", lineages["lineage_id"].tolist())
            lin = lineages[lineages["lineage_id"] == selected].iloc[0]
            st.write(f"**Status:** {lin.get('status', '')}")
            st.write(f"**Org:** {lin.get('org_token', '')}  "
                     f"**Payer category:** {lin.get('payer_category', '')}")
            st.write(f"**Gross posted:** {lin.get('gross_posted', '')}  "
                     f"**Reversed:** {lin.get('reversed', '')}  "
                     f"**Net:** {lin.get('net_observed_posted', '')}")
            member_ids = lin["record_ids"].split("|")
            bills = load_csv(run, "data", "bills.csv")
            st.subheader("Member records")
            st.dataframe(bills[bills["record_id"].isin(member_ids)])
            if not links.empty:
                l = links[(links["left_record_id"].isin(member_ids))
                          | (links["right_record_id"].isin(member_ids))]
                st.subheader("Link evidence")
                st.dataframe(l)

    elif page == "Manual review":
        st.header("Manual review queue")
        rq = load_csv(run, "module_a", "review_queue.csv")
        st.metric("Pending review items", len(rq))
        if not rq.empty:
            st.dataframe(rq)
        st.caption("Human adjudications are recorded separately in "
                   "manual_decisions.csv and never overwrite automatic output.")

    elif page == "Delay early-warning":
        st.header("Delay early-warning (module B)")
        preds = load_csv(run, "module_b", "predictions.csv")
        st.metric("Snapshots predicted", len(preds))
        if not preds.empty:
            show = preds[preds["outcome"] != "ABSTAIN"].head(100)
            if ("P_still_open_by_H" not in show.columns
                    and {"P_payment_by_H", "P_close_no_payment_by_H"} <= set(show.columns)):
                show["P_still_open_by_H"] = (
                    1.0 - show["P_payment_by_H"].astype(float)
                    - show["P_close_no_payment_by_H"].astype(float)
                ).round(4)
            st.dataframe(show)
        metrics = {}
        mp2 = os.path.join(ROOT, "outputs", "runs", run, "module_b",
                           "forecast_metrics.json")
        if os.path.exists(mp2):
            metrics = json.load(open(mp2, encoding="utf-8"))
            st.subheader("Model comparison (locked test set)")
            st.json({k: v for k, v in metrics.get("models", {}).items()})
        st.caption("Three mutually exclusive classes: payment by H, no-payment "
                   "close by H, still open. ABSTAIN means no reliable prediction.")

    elif page == "Test comparison":
        st.header("Test comparison")
        junit = os.path.join(ROOT, "outputs", "qa", "junit.xml")
        st.write(f"JUnit report: {junit if os.path.exists(junit) else 'NOT_RUN'}")
        st.caption("Acceptance tests T01-T19 are engineering-correctness checks; "
                   "they do not certify research success.")

    elif page == "Export":
        st.header("Export")
        st.write("Allowed scope: study aggregates and reports only. "
                 "Sensitive rows are excluded.")
        targets = {
            "lineages.csv": load_csv(run, "module_a", "lineages.csv"),
            "predictions.csv": load_csv(run, "module_b", "predictions.csv"),
        }
        choice = st.selectbox("Export target", list(targets))
        df = targets[choice]
        if not df.empty:
            st.download_button("Download CSV", df.to_csv(index=False),
                               file_name=choice, mime="text/csv")


if __name__ == "__main__":
    main()
