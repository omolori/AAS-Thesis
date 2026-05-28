"""Page 5 — AAS Parameters.

Tree view matching the AASX Package Explorer layout:
  SM "MotionCommand"      — expandable, editable
  SM "DynamicsParameters" — expandable, editable
  SM "RobotState"         — expandable, read-only
  SM "PerformanceKPIs"    — expandable, read-only
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


def _prop_row(name: str, unit: str, value_widget):
    """Render a single property row matching the AASX Package Explorer style."""
    col_label, col_widget = st.columns([2, 3])
    with col_label:
        st.markdown(
            f'<div style="padding-top:8px;font-size:0.88rem">'
            f'<span style="color:#51CF66;font-weight:600">Prop</span> '
            f'<span style="color:#ccd7e2">&quot;{name}&quot;</span> '
            f'<span style="color:#7a8fa6">@{{unit={unit}}}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_widget:
        return value_widget()


def _prop_row_readonly(name: str, unit: str, value: str):
    col_label, col_value = st.columns([2, 3])
    with col_label:
        st.markdown(
            f'<div style="padding-top:8px;font-size:0.88rem">'
            f'<span style="color:#51CF66;font-weight:600">Prop</span> '
            f'<span style="color:#ccd7e2">&quot;{name}&quot;</span> '
            f'<span style="color:#7a8fa6">@{{unit={unit}}}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_value:
        st.markdown(
            f'<div style="padding-top:8px;font-size:0.88rem;color:#F4D03F">'
            f'= {value}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── page ─────────────────────────────────────────────────────────────────────

st.markdown("# AAS Parameters")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.88rem;margin-bottom:8px">'
    "All parameters stored in the UR3 Asset Administration Shell, organized by submodel."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

p     = load(PARAMS_PATH)
mc_p  = p.get("motion_command", {})
dyn_p = p.get("dynamics", {})
alive = _alive() if BASYX_URL else False

color = GREEN if alive else "#E63946"
badge = "BaSyx Online" if alive else "BaSyx Offline — showing local values"
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

# ── SM MotionCommand ──────────────────────────────────────────────────────────
with st.expander('SM  "MotionCommand"   [urn:ur3:motioncommand:1]', expanded=True):

    tjp_default = mc_p.get("target_joint_positions", [0.0, -1.57, 1.2, -1.57, -1.57, 0.0])

    def _tjp_widget():
        raw = st.text_input("TargetJointPositions", label_visibility="collapsed",
                             value=_sval(mc_idx, "TargetJointPositions", str(tjp_default)),
                             key="tjp")
        try:
            parsed = ast.literal_eval(raw)
            if not (isinstance(parsed, list) and len(parsed) == 6):
                raise ValueError
            return parsed
        except (ValueError, SyntaxError):
            st.warning("Must be a list of 6 numbers.")
            return tjp_default

    target_joint_positions = _prop_row("TargetJointPositions", "rad", _tjp_widget)

    def _ss_widget():
        return st.number_input("SpeedScaling", label_visibility="collapsed",
                                value=_fval(mc_idx, "SpeedScaling", mc_p.get("speed_scaling", 0.8)),
                                min_value=0.01, max_value=1.0, step=0.01, format="%.2f", key="ss")

    speed_scaling = _prop_row("SpeedScaling", "ratio", _ss_widget)

    def _pm_widget():
        return st.number_input("PayloadMass", label_visibility="collapsed",
                                value=_fval(mc_idx, "PayloadMass", p["payload"]["mass_kg"]),
                                min_value=0.0, max_value=3.0, step=0.01, format="%.3f", key="pm")

    payload_mass = _prop_row("PayloadMass", "kg", _pm_widget)

# ── SM DynamicsParameters ─────────────────────────────────────────────────────
with st.expander('SM  "DynamicsParameters"   [urn:ur3:dynamicsparameters:1]', expanded=True):

    def _fc_widget():
        return st.number_input("FrictionCoefficient", label_visibility="collapsed",
                                value=_fval(dyn_idx, "FrictionCoefficient", dyn_p.get("friction_coefficient", 0.12)),
                                min_value=0.0, max_value=2.0, step=0.01, format="%.3f", key="fc")

    friction_coeff = _prop_row("FrictionCoefficient", "ratio", _fc_widget)

    def _cn_widget():
        return st.number_input("CurrentNoiseLevel", label_visibility="collapsed",
                                value=_fval(dyn_idx, "CurrentNoiseLevel", dyn_p.get("current_noise_level", 0.08)),
                                min_value=0.0, max_value=1.0, step=0.001, format="%.3f", key="cn")

    current_noise = _prop_row("CurrentNoiseLevel", "A", _cn_widget)

    def _cl_widget():
        return st.number_input("ControlLatency", label_visibility="collapsed",
                                value=_fval(dyn_idx, "ControlLatency", dyn_p.get("control_latency_s", 0.03)),
                                min_value=0.0, max_value=0.5, step=0.001, format="%.3f", key="cl")

    control_latency = _prop_row("ControlLatency", "s", _cl_widget)

    def _df_widget():
        return st.number_input("DampingFactor", label_visibility="collapsed",
                                value=_fval(dyn_idx, "DampingFactor", dyn_p.get("damping_factor", 0.15)),
                                min_value=0.0, max_value=2.0, step=0.01, format="%.3f", key="df")

    damping_factor = _prop_row("DampingFactor", "ratio", _df_widget)

# ── SM RobotState (read-only) ─────────────────────────────────────────────────
with st.expander('SM  "RobotState"   [urn:ur3:robotstate:1]', expanded=True):
    if rs_idx:
        _prop_row_readonly("JointPositions", "rad",     _sval(rs_idx, "JointPositions"))
        _prop_row_readonly("TCP_Pose",       "m, rad",  _sval(rs_idx, "TCP_Pose"))
        _prop_row_readonly("JointCurrents",  "A",       _sval(rs_idx, "JointCurrents"))
        _prop_row_readonly("Timestamp",      "ISO8601", _sval(rs_idx, "Timestamp"))
    else:
        st.caption("BaSyx server offline — RobotState unavailable.")

# ── SM PerformanceKPIs (read-only) ────────────────────────────────────────────
with st.expander('SM  "PerformanceKPIs"   [urn:ur3:performancekpis:1]', expanded=True):
    if kpi_idx:
        _prop_row_readonly("CycleTime",          "s", f"{_fval(kpi_idx, 'CycleTime',         0):.2f}")
        _prop_row_readonly("RMSCurrent",         "A", f"{_fval(kpi_idx, 'RMSCurrent',        0):.3f}")
        _prop_row_readonly("EnergyConsumption",  "J", f"{_fval(kpi_idx, 'EnergyConsumption', 0):.1f}")
        _prop_row_readonly("PositionError",      "m", f"{_fval(kpi_idx, 'PositionError',     0):.4f}")
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
