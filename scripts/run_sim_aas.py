"""Pipeline 3: execute the canonical trajectory on URSim with AAS parameters.

Tries BaSyx first (bidirectional loop). Falls back to the local AAS server
if BaSyx is unreachable — so the pipeline always works regardless of whether
the colleague's server is running.

BaSyx mode (full loop):
  1. READ  SimulationInputs from BaSyx  → configure trajectory
  2. RUN   trajectory on URSim
  3. WRITE computed KPIs → KPIResults on BaSyx

Local fallback mode:
  1. READ  SimulationModels from local AAS server  → payload + TCP
  2. RUN   trajectory on URSim

Usage:
    python scripts/run_sim_aas.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config  # noqa: E402
from digital_twin_core.aas_client import AASClient, BaSyxClient  # noqa: E402
from digital_twin_core.comparator import _detect_cycle_times  # noqa: E402
from digital_twin_core.recorder import save_run  # noqa: E402
from digital_twin_core.sim_runner import execute_trajectory  # noqa: E402
from digital_twin_core.trajectory import pick_and_place_trajectory  # noqa: E402

import numpy as np  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)


def _try_basyx() -> BaSyxClient | None:
    cfg = config.get("basyx_server", {})
    if not cfg:
        return None
    use_ngrok = str(cfg.get("use_ngrok", "false")).lower() == "true"
    base_url = cfg["ngrok_url"] if use_ngrok else cfg["local_url"]
    client = BaSyxClient(
        base_url=base_url,
        inputs_id=cfg["submodel_inputs_id"],
        kpi_id=cfg["submodel_kpi_id"],
        use_ngrok_header=use_ngrok,
    )
    return client if client.is_alive() else None


def _try_local_aas() -> AASClient | None:
    aas_host = config["aas_server"]["host"]
    if aas_host == "0.0.0.0":
        aas_host = "localhost"
    aas_port = int(config["aas_server"]["port"])
    client = AASClient(base_url=f"http://{aas_host}:{aas_port}/api/v3.0")
    return client if client.is_alive() else None


def _compute_kpis(metadata, samples: list, available_time_s: float) -> dict:
    t = np.array([s.wall_time - metadata.started_at_unix for s in samples])
    q = np.array([s.actual_q for s in samples])
    cycle_times = _detect_cycle_times(t, q)
    mean_ct = float(np.mean(cycle_times)) if cycle_times else 0.0
    throughput = 3600.0 / mean_ct if mean_ct > 0 else 0.0
    utilization = (sum(cycle_times) / available_time_s * 100.0) if available_time_s > 0 else 0.0
    return {
        "cycle_time_s":           mean_ct,
        "throughput_per_hour":    throughput,
        "utilization_pct":        utilization,
        "production_lead_time_s": metadata.ended_at_unix - metadata.started_at_unix,
        "cycle_times_list":       cycle_times,
    }


def main() -> int:
    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    # --- Try BaSyx first ---
    basyx = _try_basyx()
    if basyx:
        print(f"AAS source   : BaSyx  ({basyx.base_url})")
        inputs = basyx.fetch_simulation_inputs()
        print(f"  RobotMoveTime : {inputs['robot_move_time']} s  (DES parameter, used for KPI calc only)")
        print(f"  PickPlaceTime : {inputs['pick_place_time']} s")
        print(f"  QueueDelay    : {inputs['queue_delay']} s")
        print(f"  AvailableTime : {inputs['available_time']} s")

        # RobotMoveTime is a DES abstraction (seconds per move in a manufacturing
        # simulation) — not a robot speed. Use our default speed for actual motion
        # and reserve BaSyx values for KPI reporting only.
        trajectory = pick_and_place_trajectory()
        aas_params = None
        queue_delay = inputs["queue_delay"]
        available_time = inputs["available_time"]
        mode = "basyx"

    else:
        # --- Fall back to local AAS server ---
        local = _try_local_aas()
        if not local:
            print("ERROR: neither BaSyx nor the local AAS server is reachable.")
            print("Start the local server:  python scripts/start_aas_server.py")
            print("Or check BaSyx URL in config/settings.toml")
            return 1

        print(f"AAS source   : local server (BaSyx unreachable)")
        aas_params = local.fetch_simulation_models()
        print(f"  payload    : {aas_params['payload']['mass_kg']} kg  "
              f"cog={aas_params['payload']['cog']}")
        print(f"  tool_tcp   : {aas_params['tool_tcp']}")

        trajectory = pick_and_place_trajectory()
        queue_delay = 0.0
        available_time = 0.0
        mode = "local"

    print(f"\nTrajectory   : {trajectory.name}  ({trajectory.n_cycles} cycles)")
    print(f"URSim host   : {host}")
    print(f"Pipeline     : sim_aas")
    print()

    metadata, samples = execute_trajectory(
        trajectory=trajectory,
        host=host,
        pipeline="sim_aas",
        aas_params=aas_params,
        rtde_frequency_hz=freq,
        queue_delay_s=queue_delay,
    )
    save_run(db_path, metadata, samples)

    print(f"Run completed : {metadata.run_id}")
    print(f"Duration      : {metadata.ended_at_unix - metadata.started_at_unix:.1f} s")
    print(f"Samples       : {len(samples)}")

    # Write KPIs back to BaSyx if we used it
    if mode == "basyx":
        kpis = _compute_kpis(metadata, samples, available_time)
        print(f"\nKPIs:")
        print(f"  CycleTime           : {kpis['cycle_time_s']:.3f} s")
        print(f"  Throughput          : {kpis['throughput_per_hour']:.1f} cycles/hour")
        print(f"  Utilization         : {kpis['utilization_pct']:.1f} %")
        print(f"  ProductionLeadTime  : {kpis['production_lead_time_s']:.1f} s")
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
