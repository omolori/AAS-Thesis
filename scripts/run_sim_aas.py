"""Pipeline 3: execute the canonical trajectory on URSim with AAS parameters.

Fetches payload, tool TCP, calibration offsets, and friction coefficients
from the running AAS server and injects them into URSim before executing
the trajectory.  This is the AAS-enabled run that the thesis compares
against the URSim-default and real-robot baselines.

Usage:
    # AAS server must be running first:
    #   python scripts/start_aas_server.py
    python scripts/run_sim_aas.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config  # noqa: E402
from digital_twin_core.aas_client import AASClient  # noqa: E402
from digital_twin_core.recorder import save_run  # noqa: E402
from digital_twin_core.sim_runner import execute_trajectory  # noqa: E402
from digital_twin_core.trajectory import pick_and_place_trajectory  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)


def main() -> int:
    aas_host = config["aas_server"]["host"]
    if aas_host == "0.0.0.0":
        aas_host = "localhost"
    aas_port = int(config["aas_server"]["port"])
    aas_base_url = f"http://{aas_host}:{aas_port}/api/v3.0"

    client = AASClient(base_url=aas_base_url)
    if not client.is_alive():
        print("ERROR: AAS server is not reachable at", aas_base_url)
        print("Start it first: python scripts/start_aas_server.py")
        return 1

    print("AAS server  : OK")
    aas_params = client.fetch_simulation_models()

    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    trajectory = pick_and_place_trajectory()
    print(f"Trajectory  : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"URSim host  : {host}")
    print(f"Pipeline    : sim_aas  (AAS-parameterized)")
    print(f"  payload   : {aas_params['payload']['mass_kg']} kg  cog={aas_params['payload']['cog']}")
    print(f"  tool_tcp  : {aas_params['tool_tcp']}")
    print()

    metadata, samples = execute_trajectory(
        trajectory=trajectory,
        host=host,
        pipeline="sim_aas",
        aas_params=aas_params,
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
