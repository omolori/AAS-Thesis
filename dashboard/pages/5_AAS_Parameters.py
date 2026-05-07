"""Page 5 — AAS Parameters Editor.

Edit the simulation parameters stored in data/sim_params.json.
Changes take effect the next time the AAS server starts.
The Control Panel's 'Start AAS Server' button restarts it automatically.

Works on local only (file system access needed).
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.styles import inject_css, TEAL, ORANGE, GREEN, GREY
from dashboard._sidebar import render as render_sidebar
from digital_twin_core.sim_params import load, save
from config_loader import config

st.set_page_config(page_title="AAS Parameters", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

PARAMS_PATH = PROJECT_ROOT / "data" / "sim_params.json"

st.markdown("# AAS Parameters")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.88rem;margin-bottom:8px">'
    'Edit the simulation parameters injected into URSim by the AAS-enabled pipeline. '
    'Save changes then restart the AAS server on the Control Panel for them to take effect.'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

p = load(PARAMS_PATH)

# ── Payload ─────────────────────────────────────────────────────────────────
st.markdown("## Payload")
st.caption("Mass and centre of gravity of the tool/gripper attached to the TCP.")

col1, col2, col3, col4 = st.columns(4)
mass   = col1.number_input("Mass (kg)",  value=float(p["payload"]["mass_kg"]), min_value=0.0, max_value=3.0,  step=0.01, format="%.3f")
cog_x  = col2.number_input("CoG X (m)", value=float(p["payload"]["cog_x_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
cog_y  = col3.number_input("CoG Y (m)", value=float(p["payload"]["cog_y_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
cog_z  = col4.number_input("CoG Z (m)", value=float(p["payload"]["cog_z_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Tool TCP ─────────────────────────────────────────────────────────────────
st.markdown("## Tool TCP Offset")
st.caption("Position and orientation of the tool tip relative to the flange. Use PolyScope's 4-point wizard to get the real values.")

col1, col2, col3 = st.columns(3)
tcp_x  = col1.number_input("X (m)",  value=float(p["tool_tcp"]["x_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
tcp_y  = col2.number_input("Y (m)",  value=float(p["tool_tcp"]["y_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
tcp_z  = col3.number_input("Z (m)",  value=float(p["tool_tcp"]["z_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
col1, col2, col3 = st.columns(3)
tcp_rx = col1.number_input("Rx (rad)", value=float(p["tool_tcp"]["rx"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
tcp_ry = col2.number_input("Ry (rad)", value=float(p["tool_tcp"]["ry"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
tcp_rz = col3.number_input("Rz (rad)", value=float(p["tool_tcp"]["rz"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Joint Calibration Offsets ────────────────────────────────────────────────
st.markdown("## Joint Calibration Offsets (rad)")
st.caption("Kinematic calibration deltas vs nominal kinematics. Read from /root/ur-calibration.yaml on the real robot.")

calib = list(p["joint_calibration_offsets_rad"])
cols = st.columns(6)
for j in range(6):
    calib[j] = cols[j].number_input(
        f"J{j+1}", value=float(calib[j]),
        min_value=-0.1, max_value=0.1, step=0.0001, format="%.5f",
        key=f"calib_{j}",
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Friction Coefficients ────────────────────────────────────────────────────
st.markdown("## Joint Friction Coefficients")
st.caption("Coulomb (static) and viscous (speed-dependent) friction per joint. Leave at zero if unknown.")

friction = [dict(c) for c in p["joint_friction_coefficients"]]
col_headers = st.columns(6)
for j in range(6):
    col_headers[j].markdown(f'<div style="color:{TEAL};font-weight:700;text-align:center">J{j+1}</div>', unsafe_allow_html=True)

coulomb_row = st.columns(6)
viscous_row = st.columns(6)
for j in range(6):
    friction[j]["coulomb_Nm"] = coulomb_row[j].number_input(
        "Coulomb (Nm)", value=float(friction[j]["coulomb_Nm"]),
        min_value=0.0, max_value=5.0, step=0.01, format="%.3f",
        key=f"coulomb_{j}", label_visibility="visible" if j == 0 else "collapsed",
    )
    friction[j]["viscous_Nm_s_rad"] = viscous_row[j].number_input(
        "Viscous (Nm·s/rad)", value=float(friction[j]["viscous_Nm_s_rad"]),
        min_value=0.0, max_value=5.0, step=0.001, format="%.4f",
        key=f"viscous_{j}", label_visibility="visible" if j == 0 else "collapsed",
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Save ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
if col1.button("Save Parameters", type="primary", use_container_width=True):
    new_params = {
        "payload": {
            "mass_kg": mass,
            "cog_x_m": cog_x,
            "cog_y_m": cog_y,
            "cog_z_m": cog_z,
        },
        "tool_tcp": {
            "x_m": tcp_x, "y_m": tcp_y, "z_m": tcp_z,
            "rx":  tcp_rx, "ry":  tcp_ry, "rz":  tcp_rz,
        },
        "joint_calibration_offsets_rad": calib,
        "joint_friction_coefficients": friction,
    }
    save(PARAMS_PATH, new_params)
    st.success("Saved to data/sim_params.json. Go to the Control Panel and restart the AAS server to apply.")

with col2:
    st.markdown(
        '<div style="color:#7a8fa6;font-size:0.83rem;padding-top:10px">'
        'After saving, go to <b>Control Panel</b> → Stop AAS Server → Start AAS Server'
        '</div>',
        unsafe_allow_html=True,
    )
