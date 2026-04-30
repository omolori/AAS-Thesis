"""CLI tool: compare two recorded runs and print + save metrics.

Usage:
    python scripts/compare_runs.py <run_a_id> <run_b_id>

If either ID is omitted, all available runs are listed from the database.

Output:
    - A readable metrics table printed to stdout
    - A CSV file at data/comparisons/<timestamp>.csv
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config  # noqa: E402
from digital_twin_core.comparator import compare_runs, write_comparison_csv  # noqa: E402
from digital_twin_core.recorder import list_runs  # noqa: E402


def _list_runs(db_path: Path) -> None:
    runs = list_runs(db_path)
    if not runs:
        print("No runs found in", db_path)
        return
    print(f"{'run_id':<34}  {'pipeline':<12}  {'trajectory':<18}  started_at")
    print("-" * 90)
    for r in runs:
        ts = datetime.datetime.fromtimestamp(r.started_at_unix).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{r.run_id:<34}  {r.pipeline:<12}  {r.trajectory_name:<18}  {ts}")


def _print_result(result) -> None:  # type: ignore[no-untyped-def]
    sep = "-" * 60
    print(sep)
    print(f"  Run A  (baseline) : {result.run_a_id}")
    print(f"  Run B  (candidate): {result.run_b_id}")
    print(sep)

    print("\n  CYCLE TIMES")
    if result.cycle_times_a_s:
        mean_a = sum(result.cycle_times_a_s) / len(result.cycle_times_a_s)
        print(f"    A  per cycle : {[f'{t:.3f}s' for t in result.cycle_times_a_s]}  mean={mean_a:.3f}s")
    else:
        print("    A  : no cycles detected")
    if result.cycle_times_b_s:
        mean_b = sum(result.cycle_times_b_s) / len(result.cycle_times_b_s)
        print(f"    B  per cycle : {[f'{t:.3f}s' for t in result.cycle_times_b_s]}  mean={mean_b:.3f}s")
    else:
        print("    B  : no cycles detected")

    print("\n  JOINT POSITION RMSE (rad)")
    for j, v in enumerate(result.joint_rmse_rad):
        print(f"    J{j+1} : {v:.6f} rad")
    print(f"    combined : {result.joint_rmse_combined_rad:.6f} rad")

    print("\n  TCP PATH RMS DEVIATION")
    print(f"    {result.tcp_path_rms_deviation_m*1000:.3f} mm  ({result.tcp_path_rms_deviation_m:.6f} m)")

    print("\n  RMS JOINT CURRENT  (A)")
    print(f"    {'joint':<8}  {'run A':>10}  {'run B':>10}")
    for j in range(6):
        a = result.rms_current_a_per_joint[j]
        b = result.rms_current_b_per_joint[j]
        print(f"    J{j+1:<7}  {a:>10.4f}  {b:>10.4f}")

    print(sep)


def main() -> int:
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    parser = argparse.ArgumentParser(
        description="Compare two recorded UR3 runs and compute thesis metrics."
    )
    parser.add_argument("run_a_id", nargs="?", help="baseline run ID")
    parser.add_argument("run_b_id", nargs="?", help="candidate run ID")
    args = parser.parse_args()

    if args.run_a_id is None or args.run_b_id is None:
        print("Available runs:\n")
        _list_runs(db_path)
        print("\nUsage: python scripts/compare_runs.py <run_a_id> <run_b_id>")
        return 0

    result = compare_runs(db_path, args.run_a_id, args.run_b_id)
    _print_result(result)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = PROJECT_ROOT / "data" / "comparisons" / f"{timestamp}.csv"
    write_comparison_csv(result, csv_path)
    print(f"\n  CSV written to: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
