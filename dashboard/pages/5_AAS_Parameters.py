"""Page 5 — AAS Parameters Editor."""
import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from dashboard.styles import inject_css, TEAL
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
    "View and edit all parameters exposed through the UR3 Asset Administration Shell. "
    "Save changes then restart the AAS server on the Control Panel for them to take effect."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

p = load(PARAMS_PATH)

mc = p.get("motion_command", {})
dyn = p.get("dynamics", {})


# ── Motion Command submodel ──────────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Motion Command</div>",
    unsafe_allow_html=True,
)

tjp_raw = st.text_input(
    "Target Joint Positions",
    value=str(mc.get("target_joint_positions", [0.0, -1.57, 1.2, -1.57, -1.57, 0.0])),
)
try:
    target_joint_positions = ast.literal_eval(tjp_raw)
    if not (isinstance(target_joint_positions, list) and len(target_joint_positions) == 6):
        raise ValueError
except (ValueError, SyntaxError):
    st.warning("Target Joint Positions must be a list of 6 numbers, e.g. [0.0, -1.57, 1.2, -1.57, -1.57, 0.0]")
    target_joint_positions = mc.get("target_joint_positions", [0.0, -1.57, 1.2, -1.57, -1.57, 0.0])

col1, col2 = st.columns(2)
speed_scaling = col1.number_input(
    "Speed Scaling",
    value=float(mc.get("speed_scaling", 0.8)),
    min_value=0.01, max_value=1.0, step=0.01, format="%.2f",
)

st.markdown("<hr>", unsafe_allow_html=True)


# ── Dynamics Parameters submodel ─────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Dynamics Parameters</div>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
payload_mass = col1.number_input(
    "Payload Mass (kg)",
    value=float(p["payload"]["mass_kg"]),
    min_value=0.0, max_value=3.0, step=0.01, format="%.3f",
)
friction_coeff = col2.number_input(
    "Friction Coefficient",
    value=float(dyn.get("friction_coefficient", 0.12)),
    min_value=0.0, max_value=2.0, step=0.01, format="%.3f",
)

col1, col2 = st.columns(2)
current_noise = col1.number_input(
    "Current Noise Level",
    value=float(dyn.get("current_noise_level", 0.08)),
    min_value=0.0, max_value=1.0, step=0.001, format="%.3f",
)
control_latency = col2.number_input(
    "Control Latency (s)",
    value=float(dyn.get("control_latency_s", 0.03)),
    min_value=0.0, max_value=0.5, step=0.001, format="%.3f",
)

col1, col2 = st.columns(2)
damping_factor = col1.number_input(
    "Damping Factor",
    value=float(dyn.get("damping_factor", 0.15)),
    min_value=0.0, max_value=2.0, step=0.01, format="%.3f",
)

st.markdown("<hr>", unsafe_allow_html=True)


# ── Payload detail ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Payload — Centre of Gravity</div>",
    unsafe_allow_html=True,
)
st.caption("Position of the tool centre of gravity relative to the flange (metres).")

col1, col2, col3 = st.columns(3)
cog_x = col1.number_input("CoG X (m)", value=float(p["payload"]["cog_x_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
cog_y = col2.number_input("CoG Y (m)", value=float(p["payload"]["cog_y_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
cog_z = col3.number_input("CoG Z (m)", value=float(p["payload"]["cog_z_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")

st.markdown("<hr>", unsafe_allow_html=True)


# ── Tool TCP Offset ──────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Tool TCP Offset</div>",
    unsafe_allow_html=True,
)
st.caption("Position and orientation of the tool tip relative to the flange.")

col1, col2, col3 = st.columns(3)
tcp_x  = col1.number_input("X (m)",    value=float(p["tool_tcp"]["x_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
tcp_y  = col2.number_input("Y (m)",    value=float(p["tool_tcp"]["y_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
tcp_z  = col3.number_input("Z (m)",    value=float(p["tool_tcp"]["z_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
col1, col2, col3 = st.columns(3)
tcp_rx = col1.number_input("Rx (rad)", value=float(p["tool_tcp"]["rx"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
tcp_ry = col2.number_input("Ry (rad)", value=float(p["tool_tcp"]["ry"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
tcp_rz = col3.number_input("Rz (rad)", value=float(p["tool_tcp"]["rz"]), min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")

st.markdown("<hr>", unsafe_allow_html=True)


# ── Joint Calibration Offsets ────────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Joint Calibration Offsets (rad)</div>",
    unsafe_allow_html=True,
)
st.caption("Kinematic calibration deltas vs nominal kinematics.")

calib = list(p["joint_calibration_offsets_rad"])
cols = st.columns(6)
for j in range(6):
    calib[j] = cols[j].number_input(
        f"J{j+1}", value=float(calib[j]),
        min_value=-0.1, max_value=0.1, step=0.0001, format="%.5f",
        key=f"calib_{j}",
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Joint Friction Coefficients ──────────────────────────────────────────────
st.markdown(
    '<div style="text-transform:uppercase;font-size:0.78rem;'
    'letter-spacing:0.08em;color:#7a8fa6;font-weight:600;margin-bottom:12px">'
    "Joint Friction Coefficients — Per Joint</div>",
    unsafe_allow_html=True,
)
st.caption("Coulomb (static) and viscous (speed-dependent) friction per joint.")

friction = [dict(c) for c in p["joint_friction_coefficients"]]
col_headers = st.columns(6)
for j in range(6):
    col_headers[j].markdown(
        f'<div style="color:{TEAL};font-weight:700;text-align:center">J{j+1}</div>',
        unsafe_allow_html=True,
    )

coulomb_row = st.columns(6)
viscous_row = st.columns(6)
for j in range(6):
    friction[j]["coulomb_Nm"] = coulomb_row[j].number_input(
        "Coulomb (Nm)", value=float(friction[j]["coulomb_Nm"]),
        min_value=0.0, max_value=5.0, step=0.01, format="%.3f",
        key=f"coulomb_{j}",
        label_visibility="visible" if j == 0 else "collapsed",
    )
    friction[j]["viscous_Nm_s_rad"] = viscous_row[j].number_input(
        "Viscous (Nm·s/rad)", value=float(friction[j]["viscous_Nm_s_rad"]),
        min_value=0.0, max_value=5.0, step=0.001, format="%.4f",
        key=f"viscous_{j}",
        label_visibility="visible" if j == 0 else "collapsed",
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Save ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
if col1.button("Save Parameters", type="primary", use_container_width=True):
    new_params = {
        "motion_command": {
            "target_joint_positions": target_joint_positions,
            "speed_scaling": speed_scaling,
        },
        "dynamics": {
            "friction_coefficient": friction_coeff,
            "current_noise_level": current_noise,
            "control_latency_s": control_latency,
            "damping_factor": damping_factor,
        },
        "payload": {
            "mass_kg": payload_mass,
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
    st.success("Saved. Go to Control Panel and restart the AAS server to apply.")

with col2:
    st.markdown(
        '<div style="color:#7a8fa6;font-size:0.83rem;padding-top:10px">'
        "After saving, go to <b>Control Panel</b> → Stop AAS Server → Start AAS Server"
        "</div>",
        unsafe_allow_html=True,
    )
