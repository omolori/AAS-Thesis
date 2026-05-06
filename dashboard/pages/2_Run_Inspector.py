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
from dashboard.styles import inject_css, apply_plot_style, JOINT_COLORS, CARD_BG, BORDER

st.set_page_config(page_title="Run Inspector", layout="wide")
inject_css()

st.markdown("# Run Inspector")
st.markdown("<hr>", unsafe_allow_html=True)

db_path = PROJECT_ROOT / config["storage"]["db_path"]
runs = list_runs(db_path)

if not runs:
    st.warning("No runs found.")
    st.stop()

options = {
    f"{r.pipeline}  |  {datetime.datetime.fromtimestamp(r.started_at_unix).strftime('%Y-%m-%d %H:%M:%S')}  |  {r.run_id[:16]}": r.run_id
    for r in reversed(runs)
}
run_id = options[st.selectbox("Select run", list(options.keys()))]
meta, samples = load_run(db_path, run_id)

# Metadata
dur = meta.ended_at_unix - meta.started_at_unix
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Pipeline",    meta.pipeline)
col2.metric("Duration",    f"{dur:.1f} s")
col3.metric("Samples",     f"{len(samples):,}")
col4.metric("Sample Rate", f"{len(samples)/dur:.0f} Hz")
col5.metric("Trajectory",  meta.trajectory_name)

if meta.aas_params_used:
    with st.expander("AAS parameters used in this run"):
        st.json(meta.aas_params_used)

st.markdown("<hr>", unsafe_allow_html=True)

t       = np.array([s.wall_time - meta.started_at_unix for s in samples])
q       = np.array([s.actual_q for s in samples])
tcp     = np.array([s.actual_tcp_pose for s in samples])
current = np.array([s.actual_current for s in samples])

# Joint Positions
st.markdown("## Joint Positions")
fig_q = go.Figure()
for j in range(6):
    fig_q.add_trace(go.Scatter(
        x=t, y=q[:, j], name=f"J{j+1}",
        mode="lines", line=dict(color=JOINT_COLORS[j], width=1.8),
    ))
apply_plot_style(fig_q)
fig_q.update_layout(xaxis_title="Time (s)", yaxis_title="Position (rad)")
st.plotly_chart(fig_q, use_container_width=True)

# TCP + 3D
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
    apply_plot_style(fig_tcp, height=340)
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

# Joint Currents
st.markdown("## Joint Currents")
fig_cur = go.Figure()
for j in range(6):
    fig_cur.add_trace(go.Scatter(
        x=t, y=current[:, j], name=f"J{j+1}",
        mode="lines", line=dict(color=JOINT_COLORS[j], width=1.8),
    ))
apply_plot_style(fig_cur, height=340)
fig_cur.update_layout(xaxis_title="Time (s)", yaxis_title="Current (A)")
st.plotly_chart(fig_cur, use_container_width=True)

# RMS summary
st.markdown("### RMS Current per Joint")
cols = st.columns(6)
for j in range(6):
    rms = float(np.sqrt(np.mean(current[:, j] ** 2)))
    cols[j].metric(f"J{j+1}", f"{rms:.4f} A")
