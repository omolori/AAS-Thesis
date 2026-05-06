"""Page 1 — Runs Browser."""
import sys, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config_loader import config
from digital_twin_core.recorder import list_runs
from dashboard.styles import inject_css, pipeline_badge, PIPELINE_COLORS, apply_plot_style
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Runs Browser", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

st.markdown("# Runs Browser")
st.markdown("<hr>", unsafe_allow_html=True)

runs = list_runs(db_path)

if not runs:
    st.warning("No runs found. Run `python scripts/run_sim_no_aas.py` first.")
    st.stop()

rows = []
for r in runs:
    rows.append({
        "run_id":      r.run_id,
        "pipeline":    r.pipeline,
        "trajectory":  r.trajectory_name,
        "started_at":  datetime.datetime.fromtimestamp(r.started_at_unix).strftime("%d/%m/%Y %H:%M:%S"),
        "duration_s":  round(r.ended_at_unix - r.started_at_unix, 1),
        "aas_params":  r.aas_params_used is not None,
    })
df = pd.DataFrame(rows)

# Summary
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Runs",  len(df))
col2.metric("sim_no_aas",  len(df[df.pipeline == "sim_no_aas"]))
col3.metric("sim_aas",     len(df[df.pipeline == "sim_aas"]))
col4.metric("Real Robot",  len(df[df.pipeline == "real"]))

st.markdown("<br>", unsafe_allow_html=True)

# Filter
col1, _ = st.columns([2, 4])
with col1:
    sel = st.selectbox("Filter by pipeline", ["All"] + sorted(df["pipeline"].unique().tolist()))
filtered = df if sel == "All" else df[df["pipeline"] == sel]

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    column_config={
        "run_id":     st.column_config.TextColumn("Run ID", width="large"),
        "pipeline":   st.column_config.TextColumn("Pipeline"),
        "trajectory": st.column_config.TextColumn("Trajectory"),
        "started_at": st.column_config.TextColumn("Started At"),
        "duration_s": st.column_config.NumberColumn("Duration (s)", format="%.1f"),
        "aas_params": st.column_config.CheckboxColumn("AAS Params"),
    },
)

# Duration chart
if len(filtered) > 1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## Run Durations")
    fig = go.Figure()
    for pipeline, color in PIPELINE_COLORS.items():
        subset = filtered[filtered.pipeline == pipeline]
        if subset.empty:
            continue
        fig.add_trace(go.Bar(
            x=subset["started_at"],
            y=subset["duration_s"],
            name=pipeline,
            marker_color=color,
            text=[f"{v:.1f}s" for v in subset["duration_s"]],
            textposition="outside",
        ))
    apply_plot_style(fig, height=320)
    fig.update_layout(
        barmode="group",
        xaxis_title="Run",
        yaxis_title="Duration (s)",
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Copy a Run ID from the table and paste it into the Run Inspector or Comparison page.")
