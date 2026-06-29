from aas_client import *
from simulation import *
from kpi import *

import time
import json
from datetime import datetime, timezone


# ---------------------------------
# Encoded Submodel IDs
# ---------------------------------

MOTION_COMMAND = "dXJuOnVyMzptb3Rpb25jb21tYW5kOjE"

DYNAMICS = "dXJuOnVyMzpkeW5hbWljc3BhcmFtZXRlcnM6MQ"

ROBOT_STATE = "dXJuOnVyMzpyb2JvdHN0YXRlOjE"

KPIS = "dXJuOnVyMzpwZXJmb3JtYW5jZWtwaXM6MQ"


# ---------------------------------
# LAST INPUT CACHE
# ---------------------------------

last_inputs = None


# ---------------------------------
# MAIN LOOP
# ---------------------------------

try:

    while True:

        # ---------------------------------
        # READ CURRENT INPUTS
        # ---------------------------------

        current_inputs = {

            "TargetJointPositions": json.loads(
                read_property(
                    MOTION_COMMAND,
                    "TargetJointPositions"
                )
            ),

            "SpeedScaling": float(
                read_property(
                    MOTION_COMMAND,
                    "SpeedScaling"
                )
            ),

            "PayloadMass": float(
                read_property(
                    MOTION_COMMAND,
                    "PayloadMass"
                )
            ),

            "FrictionCoefficient": float(
                read_property(
                    DYNAMICS,
                    "FrictionCoefficient"
                )
            ),

            "CurrentNoiseLevel": float(
                read_property(
                    DYNAMICS,
                    "CurrentNoiseLevel"
                )
            ),

            "ControlLatency": float(
                read_property(
                    DYNAMICS,
                    "ControlLatency"
                )
            ),

            "DampingFactor": float(
                read_property(
                    DYNAMICS,
                    "DampingFactor"
                )
            )
        }

        # ---------------------------------
        # ONLY RUN WHEN INPUTS CHANGE
        # ---------------------------------

        if current_inputs != last_inputs:

            print("\n--- Input change detected ---")

            for k, v in current_inputs.items():
                print(f"{k}: {v}")

            # ---------------------------------
            # RUN SIMULATION
            # ---------------------------------

            result = simulate_motion(
                target_joints=current_inputs["TargetJointPositions"],
                speed_scaling=current_inputs["SpeedScaling"],
                friction=current_inputs["FrictionCoefficient"],
                noise_level=current_inputs["CurrentNoiseLevel"]
            )

            # ---------------------------------
            # CALCULATE KPIs
            # ---------------------------------

            rms_current = calculate_rms_current(
                result["joint_currents"]
            )

            energy = calculate_energy(
                result["joint_currents"],
                cycle_time=result["cycle_time"]
            )

            # Placeholder
            position_error = 0.0

            # ---------------------------------
            # UPDATE ROBOT STATE
            # ---------------------------------

            write_property(
                ROBOT_STATE,
                "JointPositions",
                result["joint_positions"]
            )

            write_property(
                ROBOT_STATE,
                "TCP_Pose",
                result["tcp_pose"]
            )

            write_property(
                ROBOT_STATE,
                "JointCurrents",
                result["joint_currents"]
            )

            timestamp = datetime.now(
                timezone.utc
            ).isoformat()

            write_property(
                ROBOT_STATE,
                "Timestamp",
                timestamp
            )

            # ---------------------------------
            # UPDATE KPI SUBMODEL
            # ---------------------------------

            write_property(
                KPIS,
                "CycleTime",
                result["cycle_time"]
            )

            write_property(
                KPIS,
                "RMSCurrent",
                rms_current
            )

            write_property(
                KPIS,
                "EnergyConsumption",
                energy
            )

            write_property(
                KPIS,
                "PositionError",
                position_error
            )

            # ---------------------------------
            # TERMINAL OUTPUT
            # ---------------------------------

            print("\n--- Simulation Results ---")

            print(
                f"Cycle Time: "
                f"{result['cycle_time']:.2f} s"
            )

            print(
                f"RMS Current: "
                f"{rms_current:.3f} A"
            )

            print(
                f"Energy Consumption: "
                f"{energy:.2f} J"
            )

            print(
                f"Joint Currents: "
                f"{result['joint_currents']}"
            )

            print(
                f"Joint Positions: "
                f"{result['joint_positions']}"
            )

            print("---------------------------------")

            # Save latest inputs
            last_inputs = current_inputs.copy()

        # ---------------------------------
        # LOOP DELAY
        # ---------------------------------

        time.sleep(1)

except KeyboardInterrupt:

    print("\nSimulation stopped.")