"""Page 5 — AAS Parameters.

Displays all four UR3 AAS submodels with exact property names as stored
in the AASX Package Explorer:
  - MotionCommand        [urn:ur3:motioncommand:1]       — editable
  - DynamicsParameters   [urn:ur3:dynamicsparameters:1]  — editable
  - RobotState           [urn:ur3:robotstate:1]          — read-only
  - PerformanceKPIs      [urn:ur3:performancekpis:1]     — read-only
"""
import ast
import base64
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st

from config_loader import config
from dashboard._sidebar import render as render_sidebar
from dashboard.styles import GREEN, TEAL, inject_css
from digital_twin_core.sim_params import load, save

st.set_page_config(page_title="AAS Parameters", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

PARAMS_PATH = PROJECT_ROOT / "data" / "sim_params.json"

_bcfg         = config.get("basyx_server", {})
_use_ngrok    = str(_bcfg.get("use_ngrok", "false")).lower() == "true"
BASYX_URL     = _bcfg.get("ngrok_url" if _use_ngrok else "local_url", "")
_HDRS         = {"ngrok-skip-browser-warning": "true"} if _use_ngrok else {}
INPUTS_ID     = _bcfg.get("submodel_inputs_id",     "")
DYNAMICS_ID   = _bcfg.get("submodel_dynamics_id",   "")
ROBOTSTATE_ID = _bcfg.get("submodel_robotstate_id", "")
KPI_ID        = _bcfg.get("submodel_kpi_id",        "")


# ── helpers ──────────────────────────────────────────────────────────────────

def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _fetch(sm_id: str) -> dict:
    """Fetch submodel elements as {idShort: element} dict."""
    if not sm_id:
        return {}
    try:
        r = requests.get(f"{BASYX_URL}/submodels/{_b64(sm_id)}", headers=_HDRS, timeout=5)
        if r.status_code == 200:
            return {el["idShort"]: el for el in r.json().get("submodelElements", [])}
    except Exception:
        pass
    return {}


def _patch(sm_id: str, prop: str, value) -> bool:
    try:
        url = f"{BASYX_URL}/submodels/{_b64(sm_id)}/submodel-elements/{prop}/$value"
        r = requests.patch(url, json=value, headers={**_HDRS, "Content-Type": "application/json"}, timeout=5)
        return r.status_code < 300
    except Exception:
        return False


def _val(idx: dict, key: str, default):
    el = idx.get(key)
    if el is None:
        return default
    v = el.get("value")
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return v if v is not None else default


def _str_val(idx: dict, key: str, default: str = "—") -> str:
    el = idx.get(key)
    return str(el["value"]) if el and el.get("value") is not None else default


def _alive() -> bool:
    try:
        return requests.get(f"{BASYX_URL}/submodels", headers=_HDRS, timeout=3).status_code == 200
    except Exception:
        return False


def _section(label: str) -> None:
    st.markdown(
        f'<div style="text-transform:uppercase;font-size:0.78rem;letter-spacing:0.08em;'
        f'color:#7a8fa6;font-weight:600;margin-bottom:12px">{label}</div>',
        unsafe_allow_html=True,
    )


# ── page ─────────────────────────────────────────────────────────────────────

st.markdown("# AAS Parameters")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.88rem;margin-bottom:8px">'
    "All parameters stored across the four UR3 AAS submodels. "
    "Live values are read directly from the BaSyx server when online."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

p     = load(PARAMS_PATH)
mc_p  = p.get("motion_command", {})
dyn_p = p.get("dynamics", {})
alive = _alive() if BASYX_URL else False

color = GREEN if alive else "#E63946"
label = f"BaSyx Online — {BASYX_URL}" if alive else "BaSyx Offline — showing local values"
st.markdown(
    f'<div style="display:inline-flex;align-items:center;gap:10px;background:#161C27;'
    f'border:1px solid #232B3B;border-left:3px solid {color};border-radius:8px;'
    f'padding:8px 16px;margin-bottom:16px">'
    f'<div style="width:8px;height:8px;border-radius:50%;background:{color}"></div>'
    f'<div style="color:{color};font-weight:700;font-size:0.88rem">{label}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

mc_idx  = _fetch(INPUTS_ID)     if alive else {}
dyn_idx = _fetch(DYNAMICS_ID)   if alive else {}
rs_idx  = _fetch(ROBOTSTATE_ID) if alive else {}
kpi_idx = _fetch(KPI_ID)        if alive else {}

# ── MotionCommand ─────────────────────────────────────────────────────────────
_section("MotionCommand  [urn:ur3:motioncommand:1]")

tjp_default = mc_p.get("target_joint_positions", [0.0, -1.57, 1.2, -1.57, -1.57, 0.0])
tjp_raw = st.text_input(
    "TargetJointPositions  @{unit=rad}",
    value=_str_val(mc_idx, "TargetJointPositions", str(tjp_default)),
)
try:
    target_joint_positions = ast.literal_eval(tjp_raw)
    if not (isinstance(target_joint_positions, list) and len(target_joint_positions) == 6):
        raise ValueError
except (ValueError, SyntaxError):
    st.warning("Must be a list of 6 numbers, e.g. [0.0, -1.57, 1.2, -1.57, -1.57, 0.0]")
    target_joint_positions = tjp_default

col1, col2 = st.columns(2)
speed_scaling = col1.number_input(
    "SpeedScaling  @{unit=ratio}",
    value=_val(mc_idx, "SpeedScaling", mc_p.get("speed_scaling", 0.8)),
    min_value=0.01, max_value=1.0, step=0.01, format="%.2f",
)
payload_mass = col2.number_input(
    "PayloadMass  @{unit=kg}",
    value=_val(mc_idx, "PayloadMass", p["payload"]["mass_kg"]),
    min_value=0.0, max_value=3.0, step=0.01, format="%.3f",
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── DynamicsParameters ────────────────────────────────────────────────────────
_section("DynamicsParameters  [urn:ur3:dynamicsparameters:1]")

col1, col2 = st.columns(2)
friction_coeff  = col1.number_input(
    "FrictionCoefficient  @{unit=ratio}",
    value=_val(dyn_idx, "FrictionCoefficient", dyn_p.get("friction_coefficient", 0.12)),
    min_value=0.0, max_value=2.0, step=0.01, format="%.3f",
)
current_noise = col2.number_input(
    "CurrentNoiseLevel  @{unit=A}",
    value=_val(dyn_idx, "CurrentNoiseLevel", dyn_p.get("current_noise_level", 0.08)),
    min_value=0.0, max_value=1.0, step=0.001, format="%.3f",
)

col1, col2 = st.columns(2)
control_latency = col1.number_input(
    "ControlLatency  @{unit=s}",
    value=_val(dyn_idx, "ControlLatency", dyn_p.get("control_latency_s", 0.03)),
    min_value=0.0, max_value=0.5, step=0.001, format="%.3f",
)
damping_factor = col2.number_input(
    "DampingFactor  @{unit=ratio}",
    value=_val(dyn_idx, "DampingFactor", dyn_p.get("damping_factor", 0.15)),
    min_value=0.0, max_value=2.0, step=0.01, format="%.3f",
)

st.markdown("<hr>", unsafe_allow_html=True)

# ── RobotState (read-only) ───────────────────────────────────────────────────
_section("RobotState  [urn:ur3:robotstate:1]  — read-only")

if rs_idx:
    col1, col2 = st.columns(2)
    col1.text_input("JointPositions  @{unit=rad}",  value=_str_val(rs_idx, "JointPositions"),  disabled=True)
    col2.text_input("TCP_Pose  @{unit=m, rad}",      value=_str_val(rs_idx, "TCP_Pose"),        disabled=True)
    col1, col2 = st.columns(2)
    col1.text_input("JointCurrents  @{unit=A}",      value=_str_val(rs_idx, "JointCurrents"),   disabled=True)
    col2.text_input("Timestamp  @{unit=ISO8601}",    value=_str_val(rs_idx, "Timestamp"),       disabled=True)
else:
    st.caption("BaSyx server offline — RobotState unavailable.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── PerformanceKPIs (read-only) ──────────────────────────────────────────────
_section("PerformanceKPIs  [urn:ur3:performancekpis:1]  — read-only")

if kpi_idx:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CycleTime  (s)",           f"{_val(kpi_idx, 'CycleTime',         0):.2f}")
    col2.metric("RMSCurrent  (A)",          f"{_val(kpi_idx, 'RMSCurrent',        0):.3f}")
    col3.metric("EnergyConsumption  (J)",   f"{_val(kpi_idx, 'EnergyConsumption', 0):.1f}")
    col4.metric("PositionError  (m)",       f"{_val(kpi_idx, 'PositionError',     0):.4f}")
else:
    st.caption("BaSyx server offline — PerformanceKPIs unavailable.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── SimulationModels (local AAS, collapsed) ──────────────────────────────────
with st.expander("SimulationModels — Payload Centre of Gravity", expanded=False):
    col1, col2, col3 = st.columns(3)
    cog_x = col1.number_input("CoG X (m)", value=float(p["payload"]["cog_x_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
    cog_y = col2.number_input("CoG Y (m)", value=float(p["payload"]["cog_y_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")
    cog_z = col3.number_input("CoG Z (m)", value=float(p["payload"]["cog_z_m"]), min_value=-0.5, max_value=0.5, step=0.001, format="%.4f")

with st.expander("SimulationModels — ToolTCPOffset", expanded=False):
    col1, col2, col3 = st.columns(3)
    tcp_x  = col1.number_input("X (m)",    value=float(p["tool_tcp"]["x_m"]), min_value=-0.5, max_value=0.5,   step=0.001, format="%.4f")
    tcp_y  = col2.number_input("Y (m)",    value=float(p["tool_tcp"]["y_m"]), min_value=-0.5, max_value=0.5,   step=0.001, format="%.4f")
    tcp_z  = col3.number_input("Z (m)",    value=float(p["tool_tcp"]["z_m"]), min_value=-0.5, max_value=0.5,   step=0.001, format="%.4f")
    col1, col2, col3 = st.columns(3)
    tcp_rx = col1.number_input("Rx (rad)", value=float(p["tool_tcp"]["rx"]),  min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
    tcp_ry = col2.number_input("Ry (rad)", value=float(p["tool_tcp"]["ry"]),  min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")
    tcp_rz = col3.number_input("Rz (rad)", value=float(p["tool_tcp"]["rz"]),  min_value=-3.15, max_value=3.15, step=0.001, format="%.4f")

with st.expander("SimulationModels — JointCalibrationOffsets_rad", expanded=False):
    calib = list(p["joint_calibration_offsets_rad"])
    cols  = st.columns(6)
    for j in range(6):
        calib[j] = cols[j].number_input(f"Joint{j+1}", value=float(calib[j]), min_value=-0.1, max_value=0.1, step=0.0001, format="%.5f", key=f"calib_{j}")

with st.expander("SimulationModels — JointFrictionCoefficients", expanded=False):
    friction    = [dict(c) for c in p["joint_friction_coefficients"]]
    col_headers = st.columns(6)
    for j in range(6):
        col_headers[j].markdown(f'<div style="color:{TEAL};font-weight:700;text-align:center">Joint{j+1}</div>', unsafe_allow_html=True)
    coulomb_row = st.columns(6)
    viscous_row = st.columns(6)
    for j in range(6):
        friction[j]["coulomb_Nm"] = coulomb_row[j].number_input(
            "Coulomb_Nm", value=float(friction[j]["coulomb_Nm"]),
            min_value=0.0, max_value=5.0, step=0.01, format="%.3f",
            key=f"coulomb_{j}", label_visibility="visible" if j == 0 else "collapsed",
        )
        friction[j]["viscous_Nm_s_rad"] = viscous_row[j].number_input(
            "Viscous_Nm_s_rad", value=float(friction[j]["viscous_Nm_s_rad"]),
            min_value=0.0, max_value=5.0, step=0.001, format="%.4f",
            key=f"viscous_{j}", label_visibility="visible" if j == 0 else "collapsed",
        )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Save ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
if col1.button("Save Parameters", type="primary", use_container_width=True):
    new_params = {
        "motion_command": {
            "target_joint_positions": target_joint_positions,
            "speed_scaling":          speed_scaling,
        },
        "dynamics": {
            "friction_coefficient": friction_coeff,
            "current_noise_level":  current_noise,
            "control_latency_s":    control_latency,
            "damping_factor":       damping_factor,
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
        "joint_friction_coefficients":   friction,
    }
    save(PARAMS_PATH, new_params)

    if alive:
        if INPUTS_ID:
            _patch(INPUTS_ID, "PayloadMass",  payload_mass)
            _patch(INPUTS_ID, "SpeedScaling", speed_scaling)
        if DYNAMICS_ID:
            _patch(DYNAMICS_ID, "FrictionCoefficient", friction_coeff)
            _patch(DYNAMICS_ID, "CurrentNoiseLevel",   current_noise)
            _patch(DYNAMICS_ID, "ControlLatency",      control_latency)
            _patch(DYNAMICS_ID, "DampingFactor",       damping_factor)

    st.success("Saved. Restart the AAS server on the Control Panel to apply locally.")

with col2:
    st.markdown(
        '<div style="color:#7a8fa6;font-size:0.83rem;padding-top:10px">'
        "After saving, go to <b>Control Panel</b> → Stop AAS Server → Start AAS Server"
        "</div>",
        unsafe_allow_html=True,
    )
