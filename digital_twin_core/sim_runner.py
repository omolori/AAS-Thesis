"""Trajectory executor and RTDE recorder for URSim and the physical UR3.

Drives the robot/sim through a Trajectory using RTDEControlInterface for
motion commands, while recording samples in a background thread via the
existing RTDEClient (RTDEReceiveInterface).  The same code runs against
URSim and the real UR3 -- only the host IP differs.

Maps to thesis §3.x (experiment pipelines): this is the shared execution
core for all three pipelines (real, sim_no_aas, sim_aas).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid

try:
    from rtde_control import RTDEControlInterface
except ImportError as exc:
    raise ImportError(
        "ur_rtde is not installed or RTDEControlInterface is unavailable. "
        "Run: pip install ur_rtde"
    ) from exc

from config_loader import config
from data_acquisition.rtde_client import RTDEClient, RobotSample
from digital_twin_core.recorder import RunMetadata
from digital_twin_core.trajectory import Trajectory

log = logging.getLogger(__name__)


def execute_trajectory(
    trajectory: Trajectory,
    host: str,
    pipeline: str,
    aas_params: dict | None = None,
    rtde_frequency_hz: float = 125.0,
    queue_delay_s: float = 0.0,
    *,
    i_understand_this_moves_a_real_robot: bool = False,
) -> tuple[RunMetadata, list[RobotSample]]:
    """Drive the robot/sim through *trajectory* and return all recorded samples.

    For AAS-enabled runs, pass *aas_params* (output of AASClient.fetch_simulation_models).
    Applies payload and TCP via the controller API before motion starts.

    Joint friction coefficients and calibration offsets from *aas_params* are
    stored in RunMetadata but cannot be applied directly via the UR controller API.
    # TODO (Phase 5): incorporate joint_friction_coefficients and
    # joint_calibration_offsets_rad into a correction step on the recorded data.

    Raises RuntimeError if the real-robot safety guard fires without the
    explicit override keyword argument.
    """
    _check_real_robot_guard(host, i_understand_this_moves_a_real_robot)

    run_id = uuid.uuid4().hex
    samples: list[RobotSample] = []
    stop_event = threading.Event()

    # These are set inside the try block; initialize here so the finally
    # teardown and the metadata construction always have valid references.
    started_at: float = 0.0
    ended_at: float = 0.0

    control: RTDEControlInterface | None = None
    receive_client: RTDEClient | None = None
    recorder_thread: threading.Thread | None = None

    log.info("Connecting to %s (pipeline=%s, run_id=%s)", host, pipeline, run_id)

    try:
        control = RTDEControlInterface(host)

        if aas_params is not None:
            if aas_params.get("_source") != "basyx":
                _apply_aas_params(control, aas_params)

        receive_client = RTDEClient(host, frequency_hz=rtde_frequency_hz)
        receive_client.connect()
        recorder_thread = threading.Thread(
            target=_record_loop,
            args=(receive_client, samples, stop_event),
            daemon=True,
            name="rtde-recorder",
        )
        recorder_thread.start()

        started_at = time.time()

        for cycle_num in range(trajectory.n_cycles):
            log.info("Cycle %d/%d", cycle_num + 1, trajectory.n_cycles)
            for wp in trajectory.waypoints:
                log.debug("  moveJ -> %s  %s", wp.name, wp.joint_positions_rad)
                control.moveJ(
                    list(wp.joint_positions_rad),
                    trajectory.speed_rad_s,
                    trajectory.accel_rad_s2,
                    asynchronous=False,  # block until waypoint reached
                )
                if wp.dwell_s > 0.0:
                    log.debug("  dwell %.2f s at %s", wp.dwell_s, wp.name)
                    time.sleep(wp.dwell_s)

                if queue_delay_s > 0.0 and cycle_num < trajectory.n_cycles - 1:
                    log.debug("  queue delay %.2f s", queue_delay_s)
                    time.sleep(queue_delay_s)

        ended_at = time.time()

    finally:
        stop_event.set()
        if recorder_thread is not None:
            recorder_thread.join(timeout=3.0)
        if control is not None:
            try:
                control.stopScript()
            except Exception:
                pass
            try:
                control.disconnect()
            except Exception:
                pass
        if receive_client is not None:
            receive_client.disconnect()

    if aas_params is not None:
        _warn_unapplied_params(aas_params)

    # ended_at is 0.0 only if the exception was raised before the loop started
    if ended_at == 0.0:
        ended_at = time.time()
    if started_at == 0.0:
        started_at = ended_at

    metadata = RunMetadata(
        run_id=run_id,
        started_at_unix=started_at,
        ended_at_unix=ended_at,
        pipeline=pipeline,
        host=host,
        trajectory_name=trajectory.name,
        aas_params_used=aas_params,
    )
    log.info(
        "Run %s complete: %.1f s, %d samples",
        run_id,
        ended_at - started_at,
        len(samples),
    )
    return metadata, samples


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_real_robot_guard(host: str, override: bool) -> None:
    """Raise unless the override flag is set when targeting the real robot IP."""
    real_host = config.get("real_robot", {}).get("host", "")
    if host == real_host and not override:
        raise RuntimeError(
            f"\n"
            f"  *** SAFETY GUARD FIRED ***\n"
            f"  Host {host!r} matches config[real_robot][host].\n"
            f"  This would command the PHYSICAL UR3 in the lab.\n"
            f"  If you are in the lab and have cleared the area, pass:\n"
            f"      i_understand_this_moves_a_real_robot=True\n"
            f"  to execute_trajectory().\n"
        )


def _apply_aas_params(control: RTDEControlInterface, aas_params: dict) -> None:
    """Apply payload and TCP offset from AAS params to the controller."""
    payload = aas_params.get("payload", {})
    mass = float(payload.get("mass_kg", 0.0))
    cog = [float(v) for v in payload.get("cog", [0.0, 0.0, 0.0])]
    log.info("AAS: setPayload(mass=%.3f kg, cog=%s)", mass, cog)
    control.setPayload(mass, cog)

    tcp = [float(v) for v in aas_params.get("tool_tcp", [0.0] * 6)]
    log.info("AAS: setTcp(%s)", tcp)
    control.setTcp(tcp)


def _warn_unapplied_params(aas_params: dict) -> None:
    """Warn about AAS params that are stored but can't be injected via the API."""
    offsets = aas_params.get("joint_calibration_offsets_rad", [])
    if any(v != 0.0 for v in offsets):
        log.warning(
            "AAS: joint_calibration_offsets_rad %s are non-zero but cannot be "
            "applied via the UR controller API. Stored in RunMetadata for Phase 5.",
            offsets,
        )
    friction = aas_params.get("joint_friction_coefficients", [])
    if any(c["coulomb_Nm"] != 0.0 or c["viscous_Nm_s_rad"] != 0.0 for c in friction):
        log.warning(
            "AAS: joint_friction_coefficients are non-zero but cannot be applied "
            "via the UR controller API. Stored in RunMetadata for Phase 5.",
        )


def _record_loop(
    client: RTDEClient,
    samples: list[RobotSample],
    stop_event: threading.Event,
) -> None:
    """Background thread: poll RTDE receive interface until stop_event is set."""
    period = 1.0 / client.frequency_hz
    next_tick = time.time()
    while not stop_event.is_set():
        try:
            samples.append(client.sample())
        except Exception as exc:
            log.warning("RTDE sample error (will retry): %s", exc)
        next_tick += period
        sleep_for = next_tick - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)
