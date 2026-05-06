"""Page 0 — Control Panel.

Start the AAS server, run pipelines, and stream live output —
all from the browser without touching a terminal.

Only works when running locally (URSim and AAS server must be reachable).
"""
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import psutil

from config_loader import config
from dashboard.styles import inject_css, TEAL, ORANGE, GREEN, PIPELINE_COLORS
from dashboard._sidebar import render as render_sidebar

st.set_page_config(page_title="Control Panel", layout="wide")
inject_css()

db_path = PROJECT_ROOT / config["storage"]["db_path"]
render_sidebar(db_path)

PYTHON  = sys.executable
PID_FILE = PROJECT_ROOT / "data" / ".aas_server.pid"


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

def _server_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        return pid if psutil.pid_exists(pid) else None
    except Exception:
        return None


def _start_server() -> None:
    proc = subprocess.Popen(
        [PYTHON, "scripts/start_aas_server.py"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))
    time.sleep(2)  # give the server time to bind


def _stop_server() -> None:
    pid = _server_pid()
    if pid:
        try:
            psutil.Process(pid).terminate()
        except Exception:
            pass
    PID_FILE.unlink(missing_ok=True)


def _run_script(script: str, log_placeholder) -> tuple[int, list[str]]:
    """Run a pipeline script and stream output live into log_placeholder."""
    lines: list[str] = []
    proc = subprocess.Popen(
        [PYTHON, script],
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

# ── AAS Server ──────────────────────────────────────────────────────────────
st.markdown("## AAS Server")

pid = _server_pid()
if pid:
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:10px;'
        f'background:#161C27;border:1px solid #232B3B;border-left:3px solid {GREEN};'
        f'border-radius:8px;padding:12px 20px;margin-bottom:16px">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{GREEN}"></div>'
        f'<div style="color:{GREEN};font-weight:700">Running</div>'
        f'<div style="color:#7a8fa6;font-size:0.85rem">PID {pid} &nbsp;·&nbsp; '
        f'http://localhost:{config["aas_server"]["port"]}/api/v3.0</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Stop AAS Server", use_container_width=False):
        _stop_server()
        st.rerun()
else:
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:10px;'
        f'background:#161C27;border:1px solid #232B3B;border-left:3px solid #E63946;'
        f'border-radius:8px;padding:12px 20px;margin-bottom:16px">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:#E63946"></div>'
        f'<div style="color:#E63946;font-weight:700">Stopped</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Start AAS Server", type="primary", use_container_width=False):
        with st.spinner("Starting AAS server..."):
            _start_server()
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── Pipeline Controls ───────────────────────────────────────────────────────
st.markdown("## Run Pipelines")
st.caption("URSim must be running and in Remote Control mode before running a pipeline.")

col1, col2, col3 = st.columns(3)

run_no_aas = col1.button(
    "Run sim_no_aas",
    type="primary",
    use_container_width=True,
    help="Execute the trajectory on URSim with default parameters",
)
run_aas = col2.button(
    "Run sim_aas",
    use_container_width=True,
    help="Execute the trajectory on URSim with AAS parameters applied",
)
run_both = col3.button(
    "Run Both",
    use_container_width=True,
    help="Run sim_no_aas then sim_aas back to back",
)

st.markdown("<br>", unsafe_allow_html=True)
log_area = st.empty()

# ── Execute ────────────────────────────────────────────────────────────────
last_runs: list[str] = []

if run_no_aas or run_both:
    if not _server_pid():
        st.warning("Start the AAS server first.")
    else:
        st.markdown(
            f'<div style="color:{TEAL};font-weight:700;margin-bottom:8px">'
            f'Running sim_no_aas...</div>',
            unsafe_allow_html=True,
        )
        code, lines = _run_script("scripts/run_sim_no_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":")[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_no_aas complete — run ID: `{run_id}`")
        else:
            st.error("sim_no_aas failed. Check the log above.")

if run_aas or run_both:
    if not _server_pid():
        st.warning("Start the AAS server first.")
    else:
        st.markdown(
            f'<div style="color:{ORANGE};font-weight:700;margin-bottom:8px">'
            f'Running sim_aas...</div>',
            unsafe_allow_html=True,
        )
        code, lines = _run_script("scripts/run_sim_aas.py", log_area)
        if code == 0:
            run_id = next((l.split(":")[1].strip() for l in lines if "Run completed" in l), None)
            if run_id:
                last_runs.append(run_id)
                st.success(f"sim_aas complete — run ID: `{run_id}`")
        else:
            st.error("sim_aas failed. Check the log above.")

# ── Auto-compare shortcut ───────────────────────────────────────────────────
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
