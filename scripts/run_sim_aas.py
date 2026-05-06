"""Pipeline 3: execute the canonical trajectory on URSim with BaSyx AAS parameters.

Bidirectional AAS integration:
  1. READ  SimulationInputs from BaSyx  → configure trajectory
  2. RUN   trajectory on URSim
  3. WRITE computed KPIs → KPIResults on BaSyx

This demonstrates the full reactive digital twin loop:
  AAS configures simulation → simulation runs → results flow back to AAS.

Usage:
    python scripts/run_sim_aas.py
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config  # noqa: E402
from digital_twin_core.aas_client import BaSyxClient  # noqa: E402
from digital_twin_core.comparator import _detect_cycle_times  # noqa: E402
from digital_twin_core.recorder import save_run  # noqa: E402
from digital_twin_core.sim_runner import execute_trajectory  # noqa: E402
from digital_twin_core.trajectory import pick_and_place_trajectory  # noqa: E402

import numpy as np  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)


def _build_basyx_client() -> BaSyxClient:
    cfg = config["basyx_server"]
    use_ngrok = str(cfg.get("use_ngrok", "false")).lower() == "true"
    base_url = cfg["ngrok_url"] if use_ngrok else cfg["local_url"]
    return BaSyxClient(
        base_url=base_url,
        inputs_id=cfg["submodel_inputs_id"],
        kpi_id=cfg["submodel_kpi_id"],
        use_ngrok_header=use_ngrok,
    )


def _compute_kpis(
    metadata,
    samples: list,
    available_time_s: float,
) -> dict:
    """Compute CycleTime, Throughput, Utilization, ProductionLeadTime."""
    t = np.array([s.wall_time - metadata.started_at_unix for s in samples])
    q = np.array([s.actual_q for s in samples])

    cycle_times = _detect_cycle_times(t, q)
    mean_cycle_time = float(np.mean(cycle_times)) if cycle_times else 0.0
    total_motion_time = sum(cycle_times)
    run_duration = metadata.ended_at_unix - metadata.started_at_unix

    throughput = 3600.0 / mean_cycle_time if mean_cycle_time > 0 else 0.0
    utilization = (total_motion_time / available_time_s * 100.0) if available_time_s > 0 else 0.0

    return {
        "cycle_time_s":            mean_cycle_time,
        "throughput_per_hour":     throughput,
        "utilization_pct":         utilization,
        "production_lead_time_s":  run_duration,
        "cycle_times_list":        cycle_times,
    }


def main() -> int:
    basyx = _build_basyx_client()

    print(f"BaSyx server : {basyx.base_url}")
    if not basyx.is_alive():
        print("ERROR: BaSyx server is not reachable.")
        print("Check that the server is running and the URL in settings.toml is correct.")
        return 1
    print("BaSyx server : OK")

    # 1. READ simulation inputs from BaSyx
    print("\nReading SimulationInputs from BaSyx...")
    inputs = basyx.fetch_simulation_inputs()
    print(f"  RobotMoveTime  : {inputs['robot_move_time']} rad/s")
    print(f"  PickPlaceTime  : {inputs['pick_place_time']} s")
    print(f"  QueueDelay     : {inputs['queue_delay']} s")
    print(f"  AvailableTime  : {inputs['available_time']} s")

    # 2. BUILD trajectory from AAS parameters
    trajectory = pick_and_place_trajectory(
        speed_rad_s=inputs["robot_move_time"],
        dwell_s=inputs["pick_place_time"],
    )

    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    print(f"\nTrajectory   : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"URSim host   : {host}")
    print(f"Pipeline     : sim_aas  (BaSyx-parameterized)")
    print()

    # 3. RUN trajectory on URSim
    metadata, samples = execute_trajectory(
        trajectory=trajectory,
        host=host,
        pipeline="sim_aas",
        aas_params=None,
        rtde_frequency_hz=freq,
        queue_delay_s=inputs["queue_delay"],
    )
    save_run(db_path, metadata, samples)

    print(f"Run completed : {metadata.run_id}")
    print(f"Duration      : {metadata.ended_at_unix - metadata.started_at_unix:.1f} s")
    print(f"Samples       : {len(samples)}")

    # 4. COMPUTE KPIs
    kpis = _compute_kpis(metadata, samples, inputs["available_time"])
    print(f"\nKPIs:")
    print(f"  CycleTime           : {kpis['cycle_time_s']:.3f} s  (cycles: {[f'{t:.3f}s' for t in kpis['cycle_times_list']]})")
    print(f"  Throughput          : {kpis['throughput_per_hour']:.1f} cycles/hour")
    print(f"  Utilization         : {kpis['utilization_pct']:.1f} %")
    print(f"  ProductionLeadTime  : {kpis['production_lead_time_s']:.1f} s")

    # 5. WRITE KPIs back to BaSyx
    print("\nWriting KPIResults to BaSyx...")
    basyx.write_kpi_results(
        cycle_time_s=kpis["cycle_time_s"],
        throughput_per_hour=kpis["throughput_per_hour"],
        utilization_pct=kpis["utilization_pct"],
        production_lead_time_s=kpis["production_lead_time_s"],
    )
    print("KPIResults written OK")
    print(f"\nSaved to : {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
