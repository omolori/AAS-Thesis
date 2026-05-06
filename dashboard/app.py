"""UR3 Digital Twin Dashboard — entry point.

Run with:
    streamlit run dashboard/app.py
"""
import sys, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard.styles import inject_css, pipeline_badge, TEAL, PIPELINE_COLORS
from dashboard._sidebar import render as render_sidebar

st.set_page_config(
    page_title="UR3 Digital Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

from config_loader import config
from digital_twin_core.recorder import list_runs

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)
runs = list_runs(db_path)

# --- Header ---
st.markdown(
    f"""
    <div style="padding:8px 0 4px">
        <div style="font-size:1.7rem;font-weight:800;color:#ccd7e2;letter-spacing:-0.01em">
            UR3 Digital Twin
        </div>
        <div style="font-size:0.9rem;color:#7a8fa6;margin-top:3px">
            AAS-enabled simulation comparison &mdash; AAU Thesis Project
        </div>
    </div>
    <hr>
    """,
    unsafe_allow_html=True,
)

# --- Summary metrics ---
no_aas = [r for r in runs if r.pipeline == "sim_no_aas"]
aas    = [r for r in runs if r.pipeline == "sim_aas"]
real   = [r for r in runs if r.pipeline == "real"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Runs",       len(runs))
col2.metric("sim_no_aas",       len(no_aas))
col3.metric("sim_aas",          len(aas))
col4.metric("Real Robot",       len(real))

st.markdown("<br>", unsafe_allow_html=True)

# --- Navigation cards ---
st.markdown("## Navigation")
c1, c2, c3 = st.columns(3)

card_style = (
    "background:#161C27;border:1px solid #232B3B;"
    "border-radius:8px;padding:22px 24px;height:130px"
)
for col, title, desc, accent in [
    (c1, "Runs Browser",   "View and filter all recorded runs in the database.", TEAL),
    (c2, "Run Inspector",  "Plot joint positions, TCP path, and currents for any single run.", "#9ed1fe"),
    (c3, "Comparison",     "Compare two runs with full thesis metrics and time-aligned plots.", "#ff914d"),
]:
    col.markdown(
        f'<div style="{card_style}">'
        f'<div style="font-size:1rem;font-weight:700;color:{accent};margin-bottom:8px">{title}</div>'
        f'<div style="color:#7a8fa6;font-size:0.85rem;line-height:1.5">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# --- Recent runs ---
if runs:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## Recent Runs")
    header = (
        '<div style="display:grid;grid-template-columns:130px 180px 90px 1fr;'
        'gap:12px;padding:6px 12px;color:#7a8fa6;font-size:0.75rem;'
        'letter-spacing:0.06em;text-transform:uppercase;border-bottom:1px solid #232B3B">'
        '<span>Pipeline</span><span>Started</span><span>Duration</span><span>Run ID</span></div>'
    )
    st.markdown(header, unsafe_allow_html=True)
    for r in reversed(runs[-8:]):
        ts  = datetime.datetime.fromtimestamp(r.started_at_unix).strftime("%d/%m/%Y %H:%M:%S")
        dur = f"{r.ended_at_unix - r.started_at_unix:.1f} s"
        color = PIPELINE_COLORS.get(r.pipeline, "#7a8fa6")
        st.markdown(
            f'<div style="display:grid;grid-template-columns:130px 180px 90px 1fr;'
            f'gap:12px;padding:8px 12px;border-bottom:1px solid #1a2030;align-items:center">'
            f'<span>{pipeline_badge(r.pipeline)}</span>'
            f'<span style="color:#ccd7e2;font-size:0.85rem">{ts}</span>'
            f'<span style="color:#ccd7e2;font-size:0.85rem">{dur}</span>'
            f'<span style="color:#7a8fa6;font-size:0.8rem;font-family:monospace">{r.run_id}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
