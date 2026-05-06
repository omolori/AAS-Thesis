"""Page 0 — Control Panel.

Start the AAS server, run pipelines, and stream live output —
all from the browser without touching a terminal.

Only works when running locally (URSim must be running and in Remote Control mode).
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
from dashboard.styles import inject_css, TEAL, ORANGE, GREEN
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Control Panel", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

PYTHON   = sys.executable
AAS_PORT = int(config["aas_server"]["port"])
AAS_URL  = f"http://localhost:{AAS_PORT}/api/v3.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _server_alive() -> bool:
    try:
        r = req.get(f"{AAS_URL}/shells", timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def _start_server() -> None:
    subprocess.Popen(
        [PYTHON, str(PROJECT_ROOT / "scripts" / "start_aas_server.py")],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    # Wait up to 5s for the server to start responding
    for _ in range(10):
        time.sleep(0.5)
        if _server_alive():
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


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.markdown("# Control Panel")
st.markdown("<hr>", unsafe_allow_html=True)

# ── AAS Server status ───────────────────────────────────────────────────────
st.markdown("## AAS Server")

alive = _server_alive()
dot_color = GREEN if alive else "#E63946"
status_text = "Running" if alive else "Stopped"
border_color = GREEN if alive else "#E63946"

st.markdown(
    f'<div style="display:inline-flex;align-items:center;gap:10px;'
    f'background:#161C27;border:1px solid #232B3B;border-left:3px solid {border_color};'
    f'border-radius:8px;padding:12px 20px;margin-bottom:16px">'
    f'<div style="width:10px;height:10px;border-radius:50%;background:{dot_color}"></div>'
    f'<div style="color:{dot_color};font-weight:700">{status_text}</div>'
    f'{"<div style=color:#7a8fa6;font-size:0.85rem>&nbsp;·&nbsp;" + AAS_URL + "</div>" if alive else ""}'
    f'</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 5])
if not alive:
    if col1.button("Start AAS Server", type="primary"):
        with st.spinner("Starting AAS server..."):
            _start_server()
        st.rerun()
else:
    col1.button("Running — no action needed", disabled=True)

if col2.button("Refresh status"):
    st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── Pipeline controls ────────────────────────────────────────────────────────
st.markdown("## Run Pipelines")
st.caption("URSim must be running and in Remote Control mode.")

col1, col2, col3 = st.columns(3)
run_no_aas = col1.button("Run sim_no_aas", type="primary", use_container_width=True)
run_aas    = col2.button("Run sim_aas",    use_container_width=True)
run_both   = col3.button("Run Both",       use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
log_area = st.empty()

last_runs: list[str] = []

if run_no_aas or run_both:
    if not _server_alive():
        st.warning("Start the AAS server first.")
    else:
        st.markdown(
            f'<div style="color:{TEAL};font-weight:700;margin-bottom:6px">'
            f'Running sim_no_aas...</div>',
            unsafe_allow_html=True,
        )
        code, lines = _run_script("scripts/run_sim_no_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":", 1)[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_no_aas done — `{run_id}`")
        else:
            st.error("sim_no_aas failed. See log above.")

if run_aas or run_both:
    if not _server_alive():
        st.warning("Start the AAS server first.")
    else:
        st.markdown(
            f'<div style="color:{ORANGE};font-weight:700;margin-bottom:6px">'
            f'Running sim_aas...</div>',
            unsafe_allow_html=True,
        )
        code, lines = _run_script("scripts/run_sim_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":", 1)[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_aas done — `{run_id}`")
        else:
            st.error("sim_aas failed. See log above.")

# ── Auto-compare shortcut ─────────────────────────────────────────────────
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
