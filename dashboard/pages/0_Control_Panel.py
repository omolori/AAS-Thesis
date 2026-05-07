"""Page 0 — Control Panel.

Two sections:
  - BaSyx Server   — works on local AND Streamlit Cloud (HTTP to ngrok URL)
  - Local Pipeline — only works when running locally (needs URSim)
"""
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import requests as req

from config_loader import config
from digital_twin_core.aas_client import BaSyxClient
from dashboard.styles import inject_css, TEAL, ORANGE, GREEN, GREY, PURPLE
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Control Panel", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

PYTHON   = sys.executable
AAS_PORT = int(config["aas_server"]["port"])
AAS_URL  = f"http://localhost:{AAS_PORT}/api/v3.0"

_bcfg = config.get("basyx_server", {})
_use_ngrok = str(_bcfg.get("use_ngrok", "false")).lower() == "true"
BASYX_URL  = _bcfg.get("ngrok_url" if _use_ngrok else "local_url", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _local_server_alive() -> bool:
    try:
        return req.get(f"{AAS_URL}/shells", timeout=1).status_code == 200
    except Exception:
        return False


def _basyx_client() -> BaSyxClient:
    return BaSyxClient(
        base_url=BASYX_URL,
        inputs_id=_bcfg.get("submodel_inputs_id", ""),
        kpi_id=_bcfg.get("submodel_kpi_id", ""),
        use_ngrok_header=_use_ngrok,
    )


def _start_local_server() -> None:
    subprocess.Popen(
        [PYTHON, str(PROJECT_ROOT / "scripts" / "start_aas_server.py")],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    for _ in range(10):
        time.sleep(0.5)
        if _local_server_alive():
            break


def _run_script(script: str, log_placeholder) -> tuple[int, list[str]]:
    lines: list[str] = []
    proc = subprocess.Popen(
        [PYTHON, str(PROJECT_ROOT / script)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in iter(proc.stdout.readline, ""):
        lines.append(line)
        log_placeholder.code("".join(lines[-60:]), language="bash")
    proc.stdout.close()
    proc.wait()
    return proc.returncode, lines


def _status_badge(alive: bool, label_on: str, label_off: str, url: str = "") -> None:
    color  = GREEN if alive else "#E63946"
    label  = label_on if alive else label_off
    url_html = f'<span style="color:#7a8fa6;font-size:0.83rem">&nbsp;·&nbsp;{url}</span>' if alive and url else ""
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:10px;'
        f'background:#161C27;border:1px solid #232B3B;border-left:3px solid {color};'
        f'border-radius:8px;padding:10px 18px;margin-bottom:14px">'
        f'<div style="width:9px;height:9px;border-radius:50%;background:{color}"></div>'
        f'<div style="color:{color};font-weight:700;font-size:0.9rem">{label}</div>'
        f'{url_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.markdown("# Control Panel")
st.markdown("<hr>", unsafe_allow_html=True)

# ===========================================================================
# SECTION 1 — BaSyx Server (works on cloud AND local)
# ===========================================================================
st.markdown("## BaSyx Server")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.85rem;margin-bottom:12px">'
    'Accessible from anywhere — reads simulation inputs and writes KPI results.</div>',
    unsafe_allow_html=True,
)

basyx = _basyx_client()
basyx_alive = basyx.is_alive() if BASYX_URL else False

_status_badge(basyx_alive, "Online", "Offline", BASYX_URL)

col1, col2 = st.columns([1, 5])
if col1.button("Refresh BaSyx status"):
    st.rerun()

if basyx_alive:
    try:
        inputs = basyx.fetch_simulation_inputs()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Simulation Inputs")
            st.metric("RobotMoveTime", f"{inputs['robot_move_time']} s",
                      help="Target move time per waypoint (seconds)")
            st.metric("PickPlaceTime", f"{inputs['pick_place_time']} s",
                      help="Dwell time at pick and place positions")
            st.metric("QueueDelay",   f"{inputs['queue_delay']} s",
                      help="Pause between cycles")
            st.metric("AvailableTime",f"{inputs['available_time']} s",
                      help="Total available production time for utilization calculation")
    except Exception as e:
        st.warning(f"Could not read SimulationInputs: {e}")

    # Show last KPI results
    try:
        kpi_url = f"{BASYX_URL}/submodels/{__import__('base64').urlsafe_b64encode(_bcfg.get('submodel_kpi_id','').encode()).decode().rstrip('=')}/$value"
        r = req.get(kpi_url, headers={"ngrok-skip-browser-warning": "true"} if _use_ngrok else {}, timeout=5)
        if r.status_code == 200:
            kpis = r.json()
            with col2:
                st.markdown("#### Last KPI Results")
                st.metric("CycleTime",          f"{float(kpis.get('CycleTime', 0)):.2f} s")
                st.metric("Throughput",         f"{float(kpis.get('Throughput', 0)):.2f} cycles/hr")
                st.metric("Utilization",        f"{float(kpis.get('Utilization', 0)):.1f} %")
                st.metric("ProductionLeadTime", f"{float(kpis.get('ProductionLeadTime', 0)):.2f} s")
    except Exception:
        pass
else:
    st.info("BaSyx server is offline. Start the BaSyx server to enable this section.")

st.markdown("<hr>", unsafe_allow_html=True)

# ===========================================================================
# SECTION 2 — Local Pipeline (local only)
# ===========================================================================
st.markdown("## Local Pipeline")
st.markdown(
    '<div style="color:#7a8fa6;font-size:0.85rem;margin-bottom:12px">'
    'Only works when this dashboard is running locally on the same machine as URSim.</div>',
    unsafe_allow_html=True,
)

# Local AAS server
st.markdown("### Local AAS Server")
local_alive = _local_server_alive()
_status_badge(local_alive, "Running", "Stopped", AAS_URL)

col1, col2 = st.columns([1, 5])
if not local_alive:
    if col1.button("Start AAS Server", type="primary"):
        with st.spinner("Starting..."):
            _start_local_server()
        st.rerun()
else:
    col1.button("Running — no action needed", disabled=True)
if col2.button("Refresh local status"):
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Pipeline buttons
st.markdown("### Run Pipelines")
st.caption("URSim must be running and in Remote Control mode.")

col1, col2, col3 = st.columns(3)
run_no_aas = col1.button("Run sim_no_aas", type="primary", use_container_width=True)
run_aas    = col2.button("Run sim_aas",    use_container_width=True)
run_both   = col3.button("Run Both",       use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
log_area = st.empty()
last_runs: list[str] = []

if run_no_aas or run_both:
    if not _local_server_alive():
        st.warning("Start the local AAS server first.")
    else:
        st.markdown(f'<div style="color:{TEAL};font-weight:700;margin-bottom:6px">Running sim_no_aas...</div>', unsafe_allow_html=True)
        code, lines = _run_script("scripts/run_sim_no_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":", 1)[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_no_aas done — `{run_id}`")
        else:
            st.error("sim_no_aas failed. See log above.")

if run_aas or run_both:
    if not _local_server_alive():
        st.warning("Start the local AAS server first.")
    else:
        st.markdown(f'<div style="color:{ORANGE};font-weight:700;margin-bottom:6px">Running sim_aas...</div>', unsafe_allow_html=True)
        code, lines = _run_script("scripts/run_sim_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":", 1)[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_aas done — `{run_id}`")
        else:
            st.error("sim_aas failed. See log above.")

if len(last_runs) == 2:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### Both pipelines finished")
    col1, col2 = st.columns(2)
    col1.code(f"sim_no_aas: {last_runs[0]}")
    col2.code(f"sim_aas:    {last_runs[1]}")
    if st.button("Go to Comparison", type="primary"):
        st.session_state["compare_a"] = last_runs[0]
        st.session_state["compare_b"] = last_runs[1]
        st.switch_page("pages/3_Comparison.py")
