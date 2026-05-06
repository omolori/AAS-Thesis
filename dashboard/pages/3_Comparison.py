"""Page 3 — Comparison."""
import sys, datetime as dt, io
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from config_loader import config
from digital_twin_core.recorder import list_runs, load_run
from digital_twin_core.comparator import compare_runs, write_comparison_csv, _align
from dashboard.styles import (
    inject_css, apply_plot_style,
    COLOR_A, COLOR_B, JOINT_COLORS, PIPELINE_COLORS,
    pipeline_badge, CARD_BG, BORDER, YELLOW,
)
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Comparison", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

st.markdown("# Run Comparison")
st.markdown("<hr>", unsafe_allow_html=True)

runs = list_runs(db_path)
if len(runs) < 2:
    st.warning("Need at least 2 runs.")
    st.stop()

options = {
    f"{r.pipeline}  |  {dt.datetime.fromtimestamp(r.started_at_unix).strftime('%d/%m/%Y %H:%M:%S')}  |  {r.run_id[:16]}": r.run_id
    for r in reversed(runs)
}
labels     = list(options.keys())
id_to_label = {v: k for k, v in options.items()}

# Auto-default: last sim_no_aas → A, last sim_aas → B
def _default_index(pipeline: str, fallback: int) -> int:
    for i, r in enumerate(reversed(runs)):
        if r.pipeline == pipeline:
            label = id_to_label[r.run_id]
            return labels.index(label)
    return fallback

# Pre-fill from Quick Compare session state if available
init_a = _default_index("sim_no_aas", 0)
init_b = _default_index("sim_aas", min(1, len(labels)-1))
if "compare_a" in st.session_state:
    a_label = id_to_label.get(st.session_state.pop("compare_a"), "")
    if a_label in labels:
        init_a = labels.index(a_label)
if "compare_b" in st.session_state:
    b_label = id_to_label.get(st.session_state.pop("compare_b"), "")
    if b_label in labels:
        init_b = labels.index(b_label)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:{COLOR_A};letter-spacing:0.07em;text-transform:uppercase;margin-bottom:4px">Run A — Baseline</div>', unsafe_allow_html=True)
    label_a = st.selectbox("Run A", labels, index=init_a, key="run_a", label_visibility="collapsed")
with col2:
    st.markdown(f'<div style="font-size:0.78rem;font-weight:700;color:{COLOR_B};letter-spacing:0.07em;text-transform:uppercase;margin-bottom:4px">Run B — Candidate</div>', unsafe_allow_html=True)
    label_b = st.selectbox("Run B", labels, index=init_b, key="run_b", label_visibility="collapsed")

run_a_id = options[label_a]
run_b_id = options[label_b]

if run_a_id == run_b_id:
    st.error("Select two different runs.")
    st.stop()

if not st.button("Compare Runs", type="primary"):
    st.info("Select two runs above and click Compare Runs.")
    st.stop()

with st.spinner("Loading and computing metrics..."):
    result  = compare_runs(db_path, run_a_id, run_b_id)
    meta_a, samples_a = load_run(db_path, run_a_id)
    meta_b, samples_b = load_run(db_path, run_b_id)

st.markdown("<hr>", unsafe_allow_html=True)

# Run summary row
col1, col2 = st.columns(2)
with col1:
    dur_a = meta_a.ended_at_unix - meta_a.started_at_unix
    st.markdown(
        f'<div style="background:#161C27;border:1px solid #232B3B;border-left:3px solid {COLOR_A};'
        f'border-radius:8px;padding:14px 18px">'
        f'<div style="font-size:0.78rem;color:{COLOR_A};font-weight:700;letter-spacing:0.06em;text-transform:uppercase">Run A — Baseline</div>'
        f'<div style="margin-top:6px">{pipeline_badge(meta_a.pipeline)}</div>'
        f'<div style="color:#7a8fa6;font-size:0.8rem;margin-top:6px">'
        f'{dt.datetime.fromtimestamp(meta_a.started_at_unix).strftime("%d/%m/%Y %H:%M:%S")} &nbsp;&middot;&nbsp; '
        f'{dur_a:.1f}s &nbsp;&middot;&nbsp; {len(samples_a):,} samples</div>'
        f'<div style="color:#4a5568;font-size:0.72rem;font-family:monospace;margin-top:4px">{run_a_id}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with col2:
    dur_b = meta_b.ended_at_unix - meta_b.started_at_unix
    st.markdown(
        f'<div style="background:#161C27;border:1px solid #232B3B;border-left:3px solid {COLOR_B};'
        f'border-radius:8px;padding:14px 18px">'
        f'<div style="font-size:0.78rem;color:{COLOR_B};font-weight:700;letter-spacing:0.06em;text-transform:uppercase">Run B — Candidate</div>'
        f'<div style="margin-top:6px">{pipeline_badge(meta_b.pipeline)}</div>'
        f'<div style="color:#7a8fa6;font-size:0.8rem;margin-top:6px">'
        f'{dt.datetime.fromtimestamp(meta_b.started_at_unix).strftime("%d/%m/%Y %H:%M:%S")} &nbsp;&middot;&nbsp; '
        f'{dur_b:.1f}s &nbsp;&middot;&nbsp; {len(samples_b):,} samples</div>'
        f'<div style="color:#4a5568;font-size:0.72rem;font-family:monospace;margin-top:4px">{run_b_id}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Cycle Times ──────────────────────────────────────────────────────
st.markdown("## Cycle Times")
mean_a = np.mean(result.cycle_times_a_s) if result.cycle_times_a_s else 0.0
mean_b = np.mean(result.cycle_times_b_s) if result.cycle_times_b_s else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Mean A",  f"{mean_a:.3f} s",
            help="Average time for one complete pick-and-place cycle (home → away → home)")
col2.metric("Std A",   f"{result.cycle_time_std_a_s:.3f} s",
            help="Cycle-to-cycle repeatability — lower is more consistent")
col3.metric("Mean B",  f"{mean_b:.3f} s",
            delta=f"{mean_b-mean_a:+.3f} s" if mean_a else None,
            help="Positive delta means Run B is slower than Run A")
col4.metric("Std B",   f"{result.cycle_time_std_b_s:.3f} s")

fig_ct = go.Figure()
if result.cycle_times_a_s:
    fig_ct.add_trace(go.Bar(
        x=[f"Cycle {i+1}" for i in range(len(result.cycle_times_a_s))],
        y=result.cycle_times_a_s, name="Run A", marker_color=COLOR_A,
        text=[f"{t:.2f}s" for t in result.cycle_times_a_s], textposition="outside",
    ))
if result.cycle_times_b_s:
    fig_ct.add_trace(go.Bar(
        x=[f"Cycle {i+1}" for i in range(len(result.cycle_times_b_s))],
        y=result.cycle_times_b_s, name="Run B", marker_color=COLOR_B,
        text=[f"{t:.2f}s" for t in result.cycle_times_b_s], textposition="outside",
    ))
apply_plot_style(fig_ct, height=280)
fig_ct.update_layout(barmode="group", xaxis_title="Cycle", yaxis_title="Duration (s)")
st.plotly_chart(fig_ct, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Joint RMSE ───────────────────────────────────────────────────────
st.markdown("## Joint Position RMSE")
col1, col2 = st.columns([2, 3])
with col1:
    st.markdown("<br>", unsafe_allow_html=True)
    for j in range(6):
        st.metric(f"J{j+1}", f"{result.joint_rmse_rad[j]:.6f} rad",
                  help=f"Root-mean-square difference in joint {j+1} position between the two runs (time-aligned)")
    st.metric("Combined", f"{result.joint_rmse_combined_rad:.6f} rad",
              help="RMSE across all 6 joints combined")
with col2:
    fig_rmse = go.Figure(go.Bar(
        x=[f"J{j+1}" for j in range(6)],
        y=result.joint_rmse_rad,
        marker_color=JOINT_COLORS,
        text=[f"{v:.5f}" for v in result.joint_rmse_rad],
        textposition="outside",
    ))
    apply_plot_style(fig_rmse, height=310)
    fig_rmse.update_layout(xaxis_title="Joint", yaxis_title="RMSE (rad)", showlegend=False)
    st.plotly_chart(fig_rmse, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Joint Overlay ────────────────────────────────────────────────────
st.markdown("## Joint Positions — Time-Aligned Overlay")

t_a   = np.array([s.wall_time - meta_a.started_at_unix for s in samples_a])
t_b   = np.array([s.wall_time - meta_b.started_at_unix for s in samples_b])
q_a   = np.array([s.actual_q for s in samples_a])
q_b   = np.array([s.actual_q for s in samples_b])
tcp_a = np.array([s.actual_tcp_pose[:3] for s in samples_a])
tcp_b = np.array([s.actual_tcp_pose[:3] for s in samples_b])
cur_a = np.array([s.actual_current for s in samples_a])
cur_b = np.array([s.actual_current for s in samples_b])

t_shared, q_a_r, q_b_r, tcp_a_r, tcp_b_r = _align(t_a, q_a, tcp_a, t_b, q_b, tcp_b)

selected = st.multiselect("Joints", [f"J{i+1}" for i in range(6)], default=["J1", "J2", "J3"])
fig_ov = go.Figure()
for lbl in selected:
    j = int(lbl[1]) - 1
    fig_ov.add_trace(go.Scatter(x=t_shared, y=q_a_r[:, j], name=f"{lbl} A",
                                 mode="lines", line=dict(color=COLOR_A, width=1.8)))
    fig_ov.add_trace(go.Scatter(x=t_shared, y=q_b_r[:, j], name=f"{lbl} B",
                                 mode="lines", line=dict(color=COLOR_B, width=1.8, dash="dash")))
apply_plot_style(fig_ov, height=380, rangeslider=True)
fig_ov.update_layout(xaxis_title="Time (s)", yaxis_title="Position (rad)")
st.plotly_chart(fig_ov, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── TCP Deviation ────────────────────────────────────────────────────
st.markdown("## TCP Cartesian Deviation")
col1, col2 = st.columns(2)
col1.metric("RMS Deviation", f"{result.tcp_path_rms_deviation_m*1000:.3f} mm",
            help="RMS of the 3D Euclidean distance between the two runs' TCP positions (time-aligned)")
col2.metric("Std Deviation", f"{result.tcp_path_std_deviation_m*1000:.3f} mm",
            help="Standard deviation of the per-timestep TCP distance — measures variability in tracking error")

tcp_dist = np.linalg.norm(tcp_a_r - tcp_b_r, axis=1) * 1000
fig_dev = go.Figure(go.Scatter(
    x=t_shared, y=tcp_dist, mode="lines",
    fill="tozeroy",
    line=dict(color="#cb6ce6", width=1.6),
    fillcolor="rgba(203,108,230,0.12)",
))
apply_plot_style(fig_dev, height=300, rangeslider=True)
fig_dev.update_layout(xaxis_title="Time (s)", yaxis_title="Deviation (mm)", showlegend=False)
st.plotly_chart(fig_dev, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Joint Currents ───────────────────────────────────────────────────
st.markdown("## Joint Currents")
cur_cols = st.columns(6)
for j in range(6):
    cur_cols[j].metric(
        f"J{j+1} RMS",
        f"A  {result.rms_current_a_per_joint[j]:.3f}",
        delta=f"B  {result.rms_current_b_per_joint[j]:.3f}",
        delta_color="off",
        help=f"RMS current drawn by joint {j+1} over the full run (A = amperes)"
    )

sel_joint = st.selectbox("Joint to plot", [f"J{i+1}" for i in range(6)])
j = int(sel_joint[1]) - 1
fig_cur = go.Figure()
fig_cur.add_trace(go.Scatter(x=t_a, y=cur_a[:, j], name="Run A",
                              mode="lines", line=dict(color=COLOR_A, width=1.6)))
fig_cur.add_trace(go.Scatter(x=t_b, y=cur_b[:, j], name="Run B",
                              mode="lines", line=dict(color=COLOR_B, width=1.6, dash="dash")))
apply_plot_style(fig_cur, height=300, rangeslider=True)
fig_cur.update_layout(xaxis_title="Time (s)", yaxis_title="Current (A)")
st.plotly_chart(fig_cur, use_container_width=True)

# ── Export ───────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("## Export Results")

# Build CSV in memory for download button
ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = PROJECT_ROOT / "data" / "comparisons" / f"{ts}.csv"
write_comparison_csv(result, csv_path)

with open(csv_path, "rb") as f:
    csv_bytes = f.read()

col1, col2 = st.columns([2, 4])
with col1:
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name=f"comparison_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary",
    )
with col2:
    st.caption(f"Also saved to `{csv_path}`")
