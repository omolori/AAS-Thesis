"""Comparison metrics for recorded UR3 runs.

Loads two runs from the SQLite database, time-aligns them, and computes
the four metrics used to evaluate simulation accuracy in the thesis:

  1. Cycle time per cycle
  2. Per-joint and aggregate joint-position RMSE
  3. TCP path RMS deviation (Cartesian)
  4. RMS joint current per joint

No plotting here -- that is Phase 5's job.  This module is pure:
  load → compute → return ComparisonResult + write CSV.

Maps to thesis §5.x / §7.x (evaluation metrics and comparison results).
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d  # type: ignore[import-untyped]

from digital_twin_core.recorder import RunMetadata, load_run
from digital_twin_core.trajectory import pick_and_place_trajectory


# Tolerance used to decide "the robot is at the home waypoint".
_HOME_TOLERANCE_RAD = 0.05

# Home joint positions from the canonical trajectory.
_HOME_Q = list(pick_and_place_trajectory().waypoints[0].joint_positions_rad)


@dataclass
class ComparisonResult:
    run_a_id: str
    run_b_id: str
    cycle_times_a_s: list[float]
    cycle_times_b_s: list[float]
    joint_rmse_rad: list[float]       # length 6
    joint_rmse_combined_rad: float
    tcp_path_rms_deviation_m: float
    rms_current_a_per_joint: list[float]   # length 6
    rms_current_b_per_joint: list[float]


def compare_runs(db_path: Path, run_a_id: str, run_b_id: str) -> ComparisonResult:
    """Load runs A and B, time-align them, and compute comparison metrics."""
    meta_a, samples_a = load_run(db_path, run_a_id)
    meta_b, samples_b = load_run(db_path, run_b_id)

    # Relative time axis: seconds since the run started.
    t_a = np.array([s.wall_time - meta_a.started_at_unix for s in samples_a])
    t_b = np.array([s.wall_time - meta_b.started_at_unix for s in samples_b])

    q_a = np.array([s.actual_q for s in samples_a])        # (N_a, 6)
    q_b = np.array([s.actual_q for s in samples_b])        # (N_b, 6)
    tcp_a = np.array([s.actual_tcp_pose[:3] for s in samples_a])   # (N_a, 3) XYZ
    tcp_b = np.array([s.actual_tcp_pose[:3] for s in samples_b])   # (N_b, 3)
    cur_a = np.array([s.actual_current for s in samples_a])  # (N_a, 6)
    cur_b = np.array([s.actual_current for s in samples_b])  # (N_b, 6)

    # 1. Cycle times (independent of alignment -- each run is processed alone)
    cycle_times_a = _detect_cycle_times(t_a, q_a)
    cycle_times_b = _detect_cycle_times(t_b, q_b)

    # 2-3. Resample onto shared time axis for cross-run comparison
    t_shared, q_a_r, q_b_r, tcp_a_r, tcp_b_r = _align(
        t_a, q_a, tcp_a, t_b, q_b, tcp_b
    )

    # 2. Joint-position RMSE
    diff_q = q_a_r - q_b_r                        # (N_shared, 6)
    joint_rmse = list(float(np.sqrt(np.mean(diff_q[:, j] ** 2))) for j in range(6))
    joint_rmse_combined = float(np.sqrt(np.mean(diff_q ** 2)))

    # 3. TCP Cartesian RMS deviation
    tcp_dist = np.linalg.norm(tcp_a_r - tcp_b_r, axis=1)   # (N_shared,)
    tcp_rms = float(np.sqrt(np.mean(tcp_dist ** 2)))

    # 4. RMS joint current (each run independently, over the full run)
    rms_cur_a = [float(np.sqrt(np.mean(cur_a[:, j] ** 2))) for j in range(6)]
    rms_cur_b = [float(np.sqrt(np.mean(cur_b[:, j] ** 2))) for j in range(6)]

    return ComparisonResult(
        run_a_id=run_a_id,
        run_b_id=run_b_id,
        cycle_times_a_s=cycle_times_a,
        cycle_times_b_s=cycle_times_b,
        joint_rmse_rad=joint_rmse,
        joint_rmse_combined_rad=joint_rmse_combined,
        tcp_path_rms_deviation_m=tcp_rms,
        rms_current_a_per_joint=rms_cur_a,
        rms_current_b_per_joint=rms_cur_b,
    )


def write_comparison_csv(result: ComparisonResult, output_path: Path) -> None:
    """Write a flat CSV the user can open in Excel for the thesis."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str]] = [
        ("run_a_id", result.run_a_id),
        ("run_b_id", result.run_b_id),
        ("", ""),
    ]
    for i, t in enumerate(result.cycle_times_a_s):
        rows.append((f"cycle_time_a_cycle{i+1}_s", f"{t:.4f}"))
    for i, t in enumerate(result.cycle_times_b_s):
        rows.append((f"cycle_time_b_cycle{i+1}_s", f"{t:.4f}"))
    if result.cycle_times_a_s:
        rows.append(("cycle_time_a_mean_s", f"{sum(result.cycle_times_a_s)/len(result.cycle_times_a_s):.4f}"))
    if result.cycle_times_b_s:
        rows.append(("cycle_time_b_mean_s", f"{sum(result.cycle_times_b_s)/len(result.cycle_times_b_s):.4f}"))
    rows.append(("", ""))
    for j, v in enumerate(result.joint_rmse_rad):
        rows.append((f"joint_rmse_j{j+1}_rad", f"{v:.6f}"))
    rows.append(("joint_rmse_combined_rad", f"{result.joint_rmse_combined_rad:.6f}"))
    rows.append(("", ""))
    rows.append(("tcp_path_rms_deviation_m", f"{result.tcp_path_rms_deviation_m:.6f}"))
    rows.append(("", ""))
    for j, v in enumerate(result.rms_current_a_per_joint):
        rows.append((f"rms_current_a_j{j+1}_A", f"{v:.4f}"))
    for j, v in enumerate(result.rms_current_b_per_joint):
        rows.append((f"rms_current_b_j{j+1}_A", f"{v:.4f}"))

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _near_home(q: np.ndarray) -> bool:
    """True if all 6 joints are within HOME_TOLERANCE of the home position."""
    return all(abs(q[j] - _HOME_Q[j]) < _HOME_TOLERANCE_RAD for j in range(6))


def _detect_cycle_times(t: np.ndarray, q: np.ndarray) -> list[float]:
    """Detect home→move→home cycle boundaries and return per-cycle durations.

    State machine:
        AT_HOME → MOVING  (when robot departs home)
        MOVING  → AT_HOME (when robot returns to home)
    Each AT_HOME→AT_HOME round-trip is one cycle.
    The initial idle period at home is skipped by requiring the robot to
    leave home before we start timing.
    """
    if len(t) == 0:
        return []

    cycle_times: list[float] = []
    state = "AT_HOME" if _near_home(q[0]) else "MOVING"
    cycle_start: float | None = None

    for i in range(len(t)):
        at_home = _near_home(q[i])
        if state == "AT_HOME" and not at_home:
            state = "MOVING"
            cycle_start = t[i]
        elif state == "MOVING" and at_home:
            state = "AT_HOME"
            if cycle_start is not None:
                cycle_times.append(float(t[i] - cycle_start))
                cycle_start = None

    return cycle_times


def _align(
    t_a: np.ndarray,
    q_a: np.ndarray,
    tcp_a: np.ndarray,
    t_b: np.ndarray,
    q_b: np.ndarray,
    tcp_b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Resample run_a and run_b onto a common time axis via linear interpolation.

    The shared axis spans [max(t_a[0], t_b[0]), min(t_a[-1], t_b[-1])] at
    the sample rate of the shorter run.
    """
    t_start = max(t_a[0], t_b[0])
    t_end = min(t_a[-1], t_b[-1])

    if t_end <= t_start:
        raise ValueError(
            "Runs have no overlapping time window -- cannot align for comparison."
        )

    n_points = min(len(t_a), len(t_b))
    t_shared = np.linspace(t_start, t_end, n_points)

    def resample(t: np.ndarray, data: np.ndarray) -> np.ndarray:
        cols = []
        for col in range(data.shape[1]):
            f = interp1d(t, data[:, col], kind="linear", bounds_error=False, fill_value="extrapolate")
            cols.append(f(t_shared))
        return np.stack(cols, axis=1)

    q_a_r = resample(t_a, q_a)
    q_b_r = resample(t_b, q_b)
    tcp_a_r = resample(t_a, tcp_a)
    tcp_b_r = resample(t_b, tcp_b)

    return t_shared, q_a_r, q_b_r, tcp_a_r, tcp_b_r
