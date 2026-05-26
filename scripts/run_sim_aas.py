"""Pipeline 3: execute the canonical trajectory on URSim with AAS parameters.

Usage:
    python scripts/run_sim_aas.py                  # auto: BaSyx first, local fallback
    python scripts/run_sim_aas.py --source basyx   # BaSyx only (fail if offline)
    python scripts/run_sim_aas.py --source local   # local AAS server only
    python scripts/run_sim_aas.py --source auto    # default
"""
from __future__ import annotations

import argparse
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


def _compute_kpis(metadata, samples: list) -> dict:
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
        "cycle_time_s":        mean_ct,
        "rms_current_a":       rms_combined,
        "energy_consumption_j": energy_j,
        "position_error_m":    0.0,
        "cycle_times_list":    cycle_times,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        choices=["auto", "basyx", "local"],
        default="auto",
        help="AAS server to use: auto (BaSyx first, local fallback), basyx, or local",
    )
    args = parser.parse_args()

    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    # --- Select AAS source ---
    use_basyx = args.source in ("auto", "basyx")
    use_local = args.source in ("auto", "local")

    basyx = _try_basyx() if use_basyx else None
    if basyx:
        print(f"AAS source   : BaSyx  ({basyx.base_url})")
        inputs = basyx.fetch_simulation_inputs()
        print(f"  PayloadMass   : {inputs['payload_mass_kg']} kg")
        print(f"  SpeedScaling  : {inputs['speed_scaling']}")

        from config_loader import config as _cfg
        from digital_twin_core.sim_params import load as _load_params
        _p = _load_params(PROJECT_ROOT / "data" / "sim_params.json")
        _tcp = _p["tool_tcp"]

        trajectory = pick_and_place_trajectory()
        aas_params = {
            "_source": "basyx",
            "_url": basyx.base_url,
            "payload": {
                "mass_kg": inputs["payload_mass_kg"],
                "cog": [0.0, 0.0, 0.0],
            },
            "tool_tcp": [
                _tcp["x_m"], _tcp["y_m"], _tcp["z_m"],
                _tcp["rx"],  _tcp["ry"],  _tcp["rz"],
            ],
        }
        queue_delay = 0.0
        mode = "basyx"

    else:
        if not use_local:
            print("ERROR: BaSyx server is unreachable and --source basyx was specified.")
            print("Check the BaSyx URL in config/settings.toml or use --source auto.")
            return 1
        # --- Fall back to local AAS server ---
        local = _try_local_aas()
        if not local:
            print("ERROR: neither BaSyx nor the local AAS server is reachable.")
            print("Start the local server:  python scripts/start_aas_server.py")
            print("Or check BaSyx URL in config/settings.toml")
            return 1

        print(f"AAS source   : local server (BaSyx unreachable)")
        aas_params = local.fetch_simulation_models()
        aas_params["_source"] = "local"
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
        kpis = _compute_kpis(metadata, samples)
        print(f"\nKPIs:")
        print(f"  CycleTime          : {kpis['cycle_time_s']:.3f} s")
        print(f"  RMSCurrent         : {kpis['rms_current_a']:.3f} A")
        print(f"  EnergyConsumption  : {kpis['energy_consumption_j']:.1f} J")
        print(f"  PositionError      : {kpis['position_error_m']:.4f} m")
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
            print(f"WARNING: KPI write-back to BaSyx failed: {e}")
            print("Run data is saved to database — this does not affect the experiment.")

    print(f"\nSaved to : {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
