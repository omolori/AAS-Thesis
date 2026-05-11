"""Pipeline 1: execute the canonical trajectory on the PHYSICAL UR3.

*** THIS SCRIPT COMMANDS A REAL ROBOT ***

You MUST be physically present in the lab, with:
  - The robot workspace clear of people and obstacles.
  - The e-stop within reach.
  - A second person present or lab safety protocol followed.

The script will refuse to run without --yes-i-am-in-the-lab.

For Phase 4 the user is URSim-only; this script is implemented and gated
so the real-robot step can be added in a later phase without code changes.

Usage (in the lab only):
    python scripts/run_real.py --yes-i-am-in-the-lab
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config  # noqa: E402
from digital_twin_core.recorder import save_run  # noqa: E402
from digital_twin_core.sim_runner import execute_trajectory  # noqa: E402
from digital_twin_core.trajectory import pick_and_place_trajectory  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)

_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           *** REAL ROBOT PIPELINE -- READ CAREFULLY ***      ║
║                                                              ║
║  This script will send motion commands to the physical UR3.  ║
║  Ensure:                                                     ║
║    1. The workspace is clear of people and obstacles.        ║
║    2. The e-stop is within reach and tested.                 ║
║    3. You are physically present in the lab.                 ║
║                                                              ║
║  Run with --lab to proceed.                                  ║
╚══════════════════════════════════════════════════════════════╝
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute the canonical trajectory on the physical UR3."
    )
    parser.add_argument(
        "--lab",
        action="store_true",
        dest="confirmed",
        help="Confirm you are in the lab and the robot area is safe.",
    )
    args = parser.parse_args()

    print(_BANNER)

    if not args.confirmed:
        print("Refusing to run without --lab.")
        print("This is a safety guard, not a bug.")
        return 1

    host = config["real_robot"]["host"]
    freq = float(config["real_robot"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    trajectory = pick_and_place_trajectory()
    print(f"Trajectory  : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"Robot host  : {host}")
    print(f"Pipeline    : real")
    print()

    metadata, samples = execute_trajectory(
        trajectory=trajectory,
        host=host,
        pipeline="real",
        aas_params=None,
        rtde_frequency_hz=freq,
        i_understand_this_moves_a_real_robot=True,
    )

    save_run(db_path, metadata, samples)

    print(f"Run completed : {metadata.run_id}")
    print(f"Duration      : {metadata.ended_at_unix - metadata.started_at_unix:.1f} s")
    print(f"Samples       : {len(samples)}")
    print(f"Saved to      : {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
