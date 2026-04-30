"""Pipeline 2: execute the canonical trajectory on URSim with default parameters.

No AAS parameter injection -- URSim runs with its built-in defaults.
This is the baseline that will be compared against the AAS-enabled run
and (later) the real UR3.

Usage:
    python scripts/run_sim_no_aas.py
"""
from __future__ import annotations

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


def main() -> int:
    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    trajectory = pick_and_place_trajectory()
    print(f"Trajectory : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"URSim host : {host}")
    print(f"Pipeline   : sim_no_aas  (URSim default parameters)")
    print()

    metadata, samples = execute_trajectory(
        trajectory=trajectory,
        host=host,
        pipeline="sim_no_aas",
        aas_params=None,
        rtde_frequency_hz=freq,
    )

    save_run(db_path, metadata, samples)

    print(f"Run completed : {metadata.run_id}")
    print(f"Duration      : {metadata.ended_at_unix - metadata.started_at_unix:.1f} s")
    print(f"Samples       : {len(samples)}")
    print(f"Saved to      : {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
