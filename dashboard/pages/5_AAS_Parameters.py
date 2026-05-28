"""Page 5 — AAS Parameters.

Displays the four UR3 AAS submodels as stored in the AASX Package Explorer:
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
from dashboard.styles import GREEN, inject_css
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


def _fval(idx: dict, key: str, default: float) -> float:
    el = idx.get(key)
    try:
        return float(el["value"]) if el and el.get("value") is not None else default
    except (TypeError, ValueError):
        return default


def _sval(idx: dict, key: str, default: str = "—") -> str:
    el = idx.get(key)
    return str(el["value"]) if el and el.get("value") is not None else default


def _alive() -> bool:
    try:
        return requests.get(f"{BASYX_URL}/submodels", headers=_HDRS, timeout=3).status_code == 200
    except Exception:
        return False


def _sm_header(id_short: str, urn: str) -> None:
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:12px">'
        f'<span style="font-weight:700;font-size:1rem;color:#ccd7e2">SM</span>'
        f'<span style="font-weight:700;color:#ccd7e2">&quot;{id_short}&quot;</span>'
        f'<span style="color:#7a8fa6;font-size:0.8rem">[{urn}]</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _prop_label(name: str, unit: str) -> str:
    return f'<span style="color:#ccd7e2"><b>Prop</b> &quot;{name}&quot;</span> <span style="color:#7a8fa6;font-size:0.82rem">@{{unit={unit}}}</span>'


# ── page ─────────────────────────────────────────────────────────────────────

st.markdown("# AAS Parameters")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.88rem;margin-bottom:8px">'
    "All parameters stored in the UR3 Asset Administration Shell. "
    "Live values are read from the BaSyx server when online."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

p     = load(PARAMS_PATH)
mc_p  = p.get("motion_command", {})
dyn_p = p.get("dynamics", {})
alive = _alive() if BASYX_URL else False

color = GREEN if alive else "#E63946"
badge = f"BaSyx Online" if alive else "BaSyx Offline — showing local values"
st.markdown(
    f'<div style="display:inline-flex;align-items:center;gap:10px;background:#161C27;'
    f'border:1px solid #232B3B;border-left:3px solid {color};border-radius:8px;'
    f'padding:8px 16px;margin-bottom:20px">'
    f'<div style="width:8px;height:8px;border-radius:50%;background:{color}"></div>'
    f'<div style="color:{color};font-weight:700;font-size:0.88rem">{badge}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

mc_idx  = _fetch(INPUTS_ID)     if alive else {}
dyn_idx = _fetch(DYNAMICS_ID)   if alive else {}
rs_idx  = _fetch(ROBOTSTATE_ID) if alive else {}
kpi_idx = _fetch(KPI_ID)        if alive else {}

# ── MotionCommand ─────────────────────────────────────────────────────────────
_sm_header("MotionCommand", "urn:ur3:motioncommand:1")

tjp_default = mc_p.get("target_joint_positions", [0.0, -1.57, 1.2, -1.57, -1.57, 0.0])
st.markdown(_prop_label("TargetJointPositions", "rad"), unsafe_allow_html=True)
tjp_raw = st.text_input("TargetJointPositions", label_visibility="collapsed",
                         value=_sval(mc_idx, "TargetJointPositions", str(tjp_default)))
try:
    target_joint_positions = ast.literal_eval(tjp_raw)
    if not (isinstance(target_joint_positions, list) and len(target_joint_positions) == 6):
        raise ValueError
except (ValueError, SyntaxError):
    st.warning("Must be a list of 6 numbers.")
    target_joint_positions = tjp_default

col1, col2 = st.columns(2)
with col1:
    st.markdown(_prop_label("SpeedScaling", "ratio"), unsafe_allow_html=True)
    speed_scaling = st.number_input("SpeedScaling", label_visibility="collapsed",
                                     value=_fval(mc_idx, "SpeedScaling", mc_p.get("speed_scaling", 0.8)),
                                     min_value=0.01, max_value=1.0, step=0.01, format="%.2f")
with col2:
    st.markdown(_prop_label("PayloadMass", "kg"), unsafe_allow_html=True)
    payload_mass = st.number_input("PayloadMass", label_visibility="collapsed",
                                    value=_fval(mc_idx, "PayloadMass", p["payload"]["mass_kg"]),
                                    min_value=0.0, max_value=3.0, step=0.01, format="%.3f")

st.markdown("<hr>", unsafe_allow_html=True)

# ── DynamicsParameters ────────────────────────────────────────────────────────
_sm_header("DynamicsParameters", "urn:ur3:dynamicsparameters:1")

col1, col2 = st.columns(2)
with col1:
    st.markdown(_prop_label("FrictionCoefficient", "ratio"), unsafe_allow_html=True)
    friction_coeff = st.number_input("FrictionCoefficient", label_visibility="collapsed",
                                      value=_fval(dyn_idx, "FrictionCoefficient", dyn_p.get("friction_coefficient", 0.12)),
                                      min_value=0.0, max_value=2.0, step=0.01, format="%.3f")
with col2:
    st.markdown(_prop_label("CurrentNoiseLevel", "A"), unsafe_allow_html=True)
    current_noise = st.number_input("CurrentNoiseLevel", label_visibility="collapsed",
                                     value=_fval(dyn_idx, "CurrentNoiseLevel", dyn_p.get("current_noise_level", 0.08)),
                                     min_value=0.0, max_value=1.0, step=0.001, format="%.3f")

col1, col2 = st.columns(2)
with col1:
    st.markdown(_prop_label("ControlLatency", "s"), unsafe_allow_html=True)
    control_latency = st.number_input("ControlLatency", label_visibility="collapsed",
                                       value=_fval(dyn_idx, "ControlLatency", dyn_p.get("control_latency_s", 0.03)),
                                       min_value=0.0, max_value=0.5, step=0.001, format="%.3f")
with col2:
    st.markdown(_prop_label("DampingFactor", "ratio"), unsafe_allow_html=True)
    damping_factor = st.number_input("DampingFactor", label_visibility="collapsed",
                                      value=_fval(dyn_idx, "DampingFactor", dyn_p.get("damping_factor", 0.15)),
                                      min_value=0.0, max_value=2.0, step=0.01, format="%.3f")

st.markdown("<hr>", unsafe_allow_html=True)

# ── RobotState (read-only) ───────────────────────────────────────────────────
_sm_header("RobotState", "urn:ur3:robotstate:1")

if rs_idx:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(_prop_label("JointPositions", "rad"), unsafe_allow_html=True)
        st.text_input("JointPositions", label_visibility="collapsed",
                      value=_sval(rs_idx, "JointPositions"), disabled=True)
    with col2:
        st.markdown(_prop_label("TCP_Pose", "m, rad"), unsafe_allow_html=True)
        st.text_input("TCP_Pose", label_visibility="collapsed",
                      value=_sval(rs_idx, "TCP_Pose"), disabled=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(_prop_label("JointCurrents", "A"), unsafe_allow_html=True)
        st.text_input("JointCurrents", label_visibility="collapsed",
                      value=_sval(rs_idx, "JointCurrents"), disabled=True)
    with col2:
        st.markdown(_prop_label("Timestamp", "ISO8601"), unsafe_allow_html=True)
        st.text_input("Timestamp", label_visibility="collapsed",
                      value=_sval(rs_idx, "Timestamp"), disabled=True)
else:
    st.caption("BaSyx server offline — RobotState unavailable.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── PerformanceKPIs (read-only) ──────────────────────────────────────────────
_sm_header("PerformanceKPIs", "urn:ur3:performancekpis:1")

if kpi_idx:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(_prop_label("CycleTime", "s"), unsafe_allow_html=True)
        st.metric("CycleTime", f"{_fval(kpi_idx, 'CycleTime', 0):.2f}", label_visibility="collapsed")
    with col2:
        st.markdown(_prop_label("RMSCurrent", "A"), unsafe_allow_html=True)
        st.metric("RMSCurrent", f"{_fval(kpi_idx, 'RMSCurrent', 0):.3f}", label_visibility="collapsed")
    with col3:
        st.markdown(_prop_label("EnergyConsumption", "J"), unsafe_allow_html=True)
        st.metric("EnergyConsumption", f"{_fval(kpi_idx, 'EnergyConsumption', 0):.1f}", label_visibility="collapsed")
    with col4:
        st.markdown(_prop_label("PositionError", "m"), unsafe_allow_html=True)
        st.metric("PositionError", f"{_fval(kpi_idx, 'PositionError', 0):.4f}", label_visibility="collapsed")
else:
    st.caption("BaSyx server offline — PerformanceKPIs unavailable.")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Save ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
if col1.button("Save Parameters", type="primary", use_container_width=True):
    new_params = {
        **p,
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
        "payload": {**p["payload"], "mass_kg": payload_mass},
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
