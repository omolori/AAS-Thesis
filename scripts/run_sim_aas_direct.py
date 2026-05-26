"""Pipeline 3 (direct): sim_aas via URScript on port 30001, bypassing RTDEControlInterface.

Use this when the UR dashboard server (port 29999) is unavailable in URSim.
Sends the full trajectory as a URScript program to port 30001 and records
data via RTDE on port 30004.

Usage:
    python scripts/run_sim_aas_direct.py
"""
from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config
from data_acquisition.rtde_client import RTDEClient, RobotSample
from digital_twin_core.aas_client import BaSyxClient
from digital_twin_core.comparator import _detect_cycle_times
from digital_twin_core.recorder import RunMetadata, save_run
from digital_twin_core.sim_params import load as load_params
from digital_twin_core.trajectory import pick_and_place_trajectory

import numpy as np

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")
log = logging.getLogger(__name__)

_PARAMS_PATH = PROJECT_ROOT / "data" / "sim_params.json"


def _build_urscript(trajectory, payload_mass_kg: float, tcp: list[float]) -> str:
    """Build a URScript program for the full trajectory with AAS parameters."""
    wp = trajectory.waypoints
    speed = trajectory.speed_rad_s
    accel = trajectory.accel_rad_s2
    dwell = next((w.dwell_s for w in wp if w.dwell_s > 0), 0.5)

    lines = ["def aas_trajectory():"]
    lines.append(f"  set_payload({payload_mass_kg}, [{tcp[0]}, {tcp[1]}, {tcp[2]}])")
    lines.append(f"  set_tcp(p[{tcp[0]}, {tcp[1]}, {tcp[2]}, {tcp[3]}, {tcp[4]}, {tcp[5]}])")
    lines.append(f"  i = 0")
    lines.append(f"  while i < {trajectory.n_cycles}:")
    for waypoint in wp:
        q = list(waypoint.joint_positions_rad)
        lines.append(f"    movej({q}, a={accel}, v={speed})")
        if waypoint.dwell_s > 0:
            lines.append(f"    sleep({waypoint.dwell_s})")
    lines.append(f"    i = i + 1")
    lines.append(f"  end")
    lines.append(f"end")
    lines.append(f"aas_trajectory()")
    return "\n".join(lines) + "\n"


def _send_urscript(host: str, port: int, program: str) -> None:
    """Send a URScript program to the UR primary interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(program.encode("utf-8"))
    log.info("URScript sent to %s:%d", host, port)


def _estimate_duration(trajectory) -> float:
    """Rough upper bound on run duration in seconds.

    Adds one extra cycle of headroom to account for the robot starting from
    the URSim default position and needing to move to the trajectory home first.
    """
    n_moves = len(trajectory.waypoints) * (trajectory.n_cycles + 1)
    total_dwell = sum(w.dwell_s for w in trajectory.waypoints) * trajectory.n_cycles
    move_time_est = n_moves * 5.0
    return move_time_est + total_dwell + 20.0


def _compute_kpis(metadata: RunMetadata, samples: list) -> dict:
    t = np.array([s.wall_time - metadata.started_at_unix for s in samples])
    q = np.array([s.actual_q for s in samples])
    cur = np.array([s.actual_current for s in samples])
    cycle_times = _detect_cycle_times(t, q)
    mean_ct = float(np.mean(cycle_times)) if cycle_times else 0.0
    duration = metadata.ended_at_unix - metadata.started_at_unix
    rms_per_joint = [float(np.sqrt(np.mean(cur[:, j] ** 2))) for j in range(6)]
    rms_combined = float(np.mean(rms_per_joint))
    energy_j = float(sum(rms_per_joint) * duration)
    return {
        "cycle_time_s":         mean_ct,
        "rms_current_a":        rms_combined,
        "energy_consumption_j": energy_j,
        "position_error_m":     0.0,
        "cycle_times_list":     cycle_times,
    }


def main() -> int:
    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    # --- Fetch AAS params from BaSyx ---
    cfg = config.get("basyx_server", {})
    use_ngrok = str(cfg.get("use_ngrok", "false")).lower() == "true"
    base_url = cfg["ngrok_url"] if use_ngrok else cfg["local_url"]
    basyx = BaSyxClient(
        base_url=base_url,
        inputs_id=cfg["submodel_inputs_id"],
        kpi_id=cfg["submodel_kpi_id"],
        use_ngrok_header=use_ngrok,
    )
    if basyx.is_alive():
        inputs = basyx.fetch_simulation_inputs()
        payload_mass = inputs["payload_mass_kg"]
        print(f"AAS source   : BaSyx  ({base_url})")
        print(f"  PayloadMass  : {payload_mass} kg")
        print(f"  SpeedScaling : {inputs['speed_scaling']}")
        basyx_available = True
    else:
        print(f"WARNING: BaSyx unreachable — using local sim_params.json as fallback")
        p_local = load_params(_PARAMS_PATH)
        payload_mass = p_local["payload"]["mass_kg"]
        print(f"AAS source   : local fallback")
        print(f"  PayloadMass  : {payload_mass} kg")
        basyx_available = False

    # TCP from local sim_params.json
    p = load_params(_PARAMS_PATH)
    tcp = p["tool_tcp"]
    tcp_list = [tcp["x_m"], tcp["y_m"], tcp["z_m"], tcp["rx"], tcp["ry"], tcp["rz"]]

    trajectory = pick_and_place_trajectory()
    program = _build_urscript(trajectory, payload_mass, tcp_list)

    print(f"\nTrajectory   : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"URSim host   : {host}")
    print(f"Pipeline     : sim_aas (direct URScript)")
    print()
    log.info("URScript program:\n%s", program)

    run_id = uuid.uuid4().hex
    samples: list[RobotSample] = []
    stop_event = threading.Event()
    max_duration = _estimate_duration(trajectory)

    receive_client = RTDEClient(host, frequency_hz=freq)
    receive_client.connect()

    recorder_thread = threading.Thread(
        target=_record_loop,
        args=(receive_client, samples, stop_event),
        daemon=True,
        name="rtde-recorder",
    )
    recorder_thread.start()

    started_at = time.time()
    log.info("Starting recording, then sending URScript (run_id=%s)", run_id)

    # Brief pause so the recorder gets a few samples before motion starts
    time.sleep(0.5)
    _send_urscript(host, 30001, program)

    # Wait for trajectory to complete (poll RTDE for robot returning home)
    log.info("Waiting up to %.0f s for trajectory to complete...", max_duration)
    deadline = started_at + max_duration
    while time.time() < deadline:
        time.sleep(1.0)
        elapsed = time.time() - started_at
        if elapsed > 10 and samples:
            import numpy as _np
            from digital_twin_core.comparator import _detect_cycle_times as _dct
            t_arr = _np.array([s.wall_time - started_at for s in samples])
            q_arr = _np.array([s.actual_q for s in samples])
            cycles = _dct(t_arr, q_arr)
            log.info("  %.0f s — %d samples, %d/%d cycles detected",
                     elapsed, len(samples), len(cycles), trajectory.n_cycles)
            if len(cycles) >= trajectory.n_cycles:
                log.info("All cycles complete — stopping recording.")
                time.sleep(1.0)
                break

    ended_at = time.time()
    stop_event.set()
    recorder_thread.join(timeout=3.0)
    receive_client.disconnect()

    metadata = RunMetadata(
        run_id=run_id,
        started_at_unix=started_at,
        ended_at_unix=ended_at,
        pipeline="sim_aas",
        host=host,
        trajectory_name=trajectory.name,
        aas_params_used={
            "_source": "basyx_direct",
            "payload": {"mass_kg": payload_mass, "cog": [0, 0, 0]},
            "tool_tcp": tcp_list,
        },
    )
    save_run(db_path, metadata, samples)

    print(f"Run completed : {metadata.run_id}")
    print(f"Duration      : {ended_at - started_at:.1f} s")
    print(f"Samples       : {len(samples)}")

    kpis = _compute_kpis(metadata, samples)
    print(f"\nKPIs:")
    print(f"  CycleTime          : {kpis['cycle_time_s']:.3f} s")
    print(f"  RMSCurrent         : {kpis['rms_current_a']:.3f} A")
    print(f"  EnergyConsumption  : {kpis['energy_consumption_j']:.1f} J")
    print(f"  Cycles detected    : {len(kpis['cycle_times_list'])}")

    if kpis['cycle_time_s'] > 0 and basyx_available:
        print("\nWriting PerformanceKPIs to BaSyx...")
        try:
            basyx.write_kpi_results(
                cycle_time_s=kpis["cycle_time_s"],
                rms_current_a=kpis["rms_current_a"],
                energy_consumption_j=kpis["energy_consumption_j"],
                position_error_m=kpis["position_error_m"],
            )
            print("PerformanceKPIs written OK")
        except Exception as e:
            print(f"WARNING: KPI write-back failed: {e}")

    print(f"\nSaved to : {db_path}")
    return 0


def _record_loop(client: RTDEClient, samples: list, stop_event: threading.Event) -> None:
    period = 1.0 / client.frequency_hz
    next_tick = time.time()
    while not stop_event.is_set():
        try:
            samples.append(client.sample())
        except Exception as exc:
            log.warning("RTDE sample error: %s", exc)
        next_tick += period
        sleep_for = next_tick - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
