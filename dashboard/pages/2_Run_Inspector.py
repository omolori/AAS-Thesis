"""Page 2 — Run Inspector."""
import sys, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from config_loader import config
from digital_twin_core.recorder import list_runs, load_run
from digital_twin_core.comparator import _detect_cycle_times
from dashboard.styles import inject_css, apply_plot_style, JOINT_COLORS, CARD_BG, BORDER, TEAL, YELLOW
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Run Inspector", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

st.markdown("# Run Inspector")
st.markdown("<hr>", unsafe_allow_html=True)

runs = list_runs(db_path)
if not runs:
    st.warning("No runs found.")
    st.stop()

options = {
    f"{r.pipeline}  |  {datetime.datetime.fromtimestamp(r.started_at_unix).strftime('%d/%m/%Y %H:%M:%S')}  |  {r.run_id[:16]}": r.run_id
    for r in reversed(runs)
}
run_id = options[st.selectbox("Select run", list(options.keys()))]
meta, samples = load_run(db_path, run_id)

dur = meta.ended_at_unix - meta.started_at_unix
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Pipeline",    meta.pipeline)
col2.metric("Duration",    f"{dur:.1f} s",          help="Wall-clock time from first to last sample")
col3.metric("Samples",     f"{len(samples):,}",     help="Total RTDE samples recorded at ~125 Hz")
col4.metric("Sample Rate", f"{len(samples)/dur:.0f} Hz")
col5.metric("Trajectory",  meta.trajectory_name)

if meta.aas_params_used:
    source = meta.aas_params_used.get("_source", "local")
    color  = "#0097b2" if source == "local" else "#ff914d"
    label  = "Local AAS Server" if source == "local" else f"BaSyx  {meta.aas_params_used.get('_url','')}"
    st.markdown(
        f'<span style="color:#7a8fa6;font-size:0.83rem">AAS Source: </span>'
        f'<span style="background:{color};color:#0E1117;padding:2px 10px;'
        f'border-radius:4px;font-size:0.78rem;font-weight:700">{label}</span>',
        unsafe_allow_html=True,
    )
    with st.expander("AAS parameters used in this run"):
        st.json(meta.aas_params_used)

st.markdown("<hr>", unsafe_allow_html=True)

t       = np.array([s.wall_time - meta.started_at_unix for s in samples])
q       = np.array([s.actual_q for s in samples])
tcp     = np.array([s.actual_tcp_pose for s in samples])
current = np.array([s.actual_current for s in samples])

# Detect cycle boundaries for markers
cycle_times = _detect_cycle_times(t, q)

def add_cycle_markers(fig: go.Figure, t_arr: np.ndarray, q_arr: np.ndarray) -> None:
    """Add vertical lines at detected cycle boundaries."""
    from digital_twin_core.trajectory import pick_and_place_trajectory
    HOME_Q = list(pick_and_place_trajectory().waypoints[0].joint_positions_rad)
    HOME_TOL = 0.05
    in_cycle = False
    for i in range(len(t_arr)):
        at_home = all(abs(q_arr[i, j] - HOME_Q[j]) < HOME_TOL for j in range(6))
        if not in_cycle and not at_home:
            in_cycle = True
        elif in_cycle and at_home:
            in_cycle = False
            fig.add_vline(
                x=float(t_arr[i]),
                line=dict(color=YELLOW, width=1, dash="dot"),
                annotation_text="home",
                annotation_font=dict(color=YELLOW, size=10),
            )

# ── Joint Positions ──────────────────────────────────────────────────
st.markdown("## Joint Positions")
if cycle_times:
    st.caption(f"Detected {len(cycle_times)} cycles — dotted lines mark home waypoint returns")

fig_q = go.Figure()
for j in range(6):
    fig_q.add_trace(go.Scatter(
        x=t, y=q[:, j], name=f"J{j+1}",
        mode="lines", line=dict(color=JOINT_COLORS[j], width=1.8),
    ))
add_cycle_markers(fig_q, t, q)
apply_plot_style(fig_q, rangeslider=True)
fig_q.update_layout(xaxis_title="Time (s)", yaxis_title="Position (rad)")
st.plotly_chart(fig_q, use_container_width=True)

# ── Cycle time summary ───────────────────────────────────────────────
if cycle_times:
    st.markdown("### Detected Cycle Times")
    cols = st.columns(len(cycle_times) + 2)
    for i, ct in enumerate(cycle_times):
        cols[i].metric(f"Cycle {i+1}", f"{ct:.3f} s")
    cols[-2].metric("Mean", f"{np.mean(cycle_times):.3f} s")
    cols[-1].metric("Std",  f"{np.std(cycle_times):.3f} s")

st.markdown("<hr>", unsafe_allow_html=True)

# ── TCP ──────────────────────────────────────────────────────────────
st.markdown("## TCP Pose")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### X / Y / Z over time")
    fig_tcp = go.Figure()
    for i, (lbl, clr) in enumerate(zip(["X", "Y", "Z"], ["#ff914d", "#0097b2", "#86e85c"])):
        fig_tcp.add_trace(go.Scatter(
            x=t, y=tcp[:, i], name=lbl,
            mode="lines", line=dict(color=clr, width=1.8),
        ))
    apply_plot_style(fig_tcp, height=340, rangeslider=True)
    fig_tcp.update_layout(xaxis_title="Time (s)", yaxis_title="Position (m)")
    st.plotly_chart(fig_tcp, use_container_width=True)

with col2:
    st.markdown("### 3D Path")
    fig_3d = go.Figure(go.Scatter3d(
        x=tcp[:, 0], y=tcp[:, 1], z=tcp[:, 2],
        mode="lines",
        line=dict(color=t, colorscale="Teal", width=4),
    ))
    fig_3d.update_layout(
        paper_bgcolor=CARD_BG,
        scene=dict(
            xaxis=dict(title="X (m)", gridcolor=BORDER, backgroundcolor="#0E1117"),
            yaxis=dict(title="Y (m)", gridcolor=BORDER, backgroundcolor="#0E1117"),
            zaxis=dict(title="Z (m)", gridcolor=BORDER, backgroundcolor="#0E1117"),
        ),
        font=dict(color="#ccd7e2"),
        margin=dict(l=0, r=0, t=20, b=0),
        height=340,
    )
    st.plotly_chart(fig_3d, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Joint Currents ────────────────────────────────────────────────────
st.markdown("## Joint Currents")
fig_cur = go.Figure()
for j in range(6):
    fig_cur.add_trace(go.Scatter(
        x=t, y=current[:, j], name=f"J{j+1}",
        mode="lines", line=dict(color=JOINT_COLORS[j], width=1.8),
    ))
add_cycle_markers(fig_cur, t, q)
apply_plot_style(fig_cur, height=340, rangeslider=True)
fig_cur.update_layout(xaxis_title="Time (s)", yaxis_title="Current (A)")
st.plotly_chart(fig_cur, use_container_width=True)

# RMS summary
st.markdown("### RMS Current per Joint")
cols = st.columns(6)
for j in range(6):
    rms = float(np.sqrt(np.mean(current[:, j] ** 2)))
    cols[j].metric(f"J{j+1}", f"{rms:.4f} A", help=f"Root-mean-square current for joint {j+1} over the full run")

# ── Quick Compare ─────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("### Quick Compare")
st.caption("Compare this run against another run without leaving the page.")

other_options = {k: v for k, v in options.items() if v != run_id}
if other_options:
    col1, col2 = st.columns([4, 1])
    with col1:
        other_label = st.selectbox("Compare with", list(other_options.keys()), key="quick_compare")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        go_compare = st.button("Go to Comparison", use_container_width=True)

    if go_compare:
        st.session_state["compare_a"] = run_id
        st.session_state["compare_b"] = other_options[other_label]
        st.switch_page("pages/3_Comparison.py")
