"""Smoke test: confirm the host can read joint data from URSim via RTDE.

Run this AFTER:
    1. URSim is running in your VMware VM
    2. A robot program is loaded (does not need to be playing)
    3. config/settings.toml has the correct ursim.host IP

Expected output: 5 seconds of joint angles printed at ~10 Hz.
If this works, the foundation is solid and we can move on to AAS modeling.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure project root on sys.path so we can import sibling packages
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config
from data_acquisition.rtde_client import RTDEClient


def rad_to_deg(values: list[float]) -> list[float]:
    return [round(math.degrees(v), 2) for v in values]


def main() -> int:
    host = config["ursim"]["host"]
    freq = float(config["ursim"]["rtde_frequency_hz"])

    print(f"Connecting to URSim at {host}:30004 (RTDE @ {freq:.0f} Hz)...")
    try:
        with RTDEClient(host, frequency_hz=freq) as client:
            print("Connected. Reading joint positions for 5 seconds...\n")
            print(f"{'t (s)':>7}  {'J1':>8} {'J2':>8} {'J3':>8} "
                  f"{'J4':>8} {'J5':>8} {'J6':>8}  state")
            print("-" * 78)

            t0 = None
            count = 0
            # Print at ~10 Hz even though sampling is faster, so the terminal
            # stays readable.
            print_period = 0.1
            next_print = 0.0

            for sample in client.stream(duration_s=5.0):
                if t0 is None:
                    t0 = sample.wall_time
                t_rel = sample.wall_time - t0
                count += 1

                if t_rel >= next_print:
                    q_deg = rad_to_deg(sample.actual_q)
                    print(f"{t_rel:7.2f}  "
                          f"{q_deg[0]:8.2f} {q_deg[1]:8.2f} {q_deg[2]:8.2f} "
                          f"{q_deg[3]:8.2f} {q_deg[4]:8.2f} {q_deg[5]:8.2f}  "
                          f"{sample.runtime_state}")
                    next_print += print_period

            print(f"\nTotal samples received: {count}")
            print("RTDE connection works. Foundation is good.")
        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print(f"  1. Can your Windows host ping {host}?", file=sys.stderr)
        print("  2. Is URSim running and a robot program loaded?", file=sys.stderr)
        print("  3. In VMware: VM > Settings > Network -> NAT or Bridged?",
              file=sys.stderr)
        print("  4. Inside URSim: Setup Robot > Network -> DHCP enabled?",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
