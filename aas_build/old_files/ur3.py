import requests
import time
import base64
from datetime import datetime, timezone

BASE_URL = "http://localhost:8081"


# -------------------------
# Base64 encode submodel IDs
# -------------------------
def b64(id_str):
    return base64.urlsafe_b64encode(id_str.encode()).decode().rstrip("=")


SM_INPUTS  = b64("urn:ur3:simulationinputs:1")
SM_RESULTS = b64("urn:ur3:kpiresults:1")
SM_MODEL   = b64("urn:ur3:simulationmodel:1")


# -------------------------
# READ PROPERTY
# -------------------------
def get_property(sm_id, prop):
    url = f"{BASE_URL}/submodels/{sm_id}/submodel-elements/{prop}"

    r = requests.get(url)
    r.raise_for_status()

    return float(r.json()["value"])


# -------------------------
# WRITE PROPERTY
# -------------------------
def put_property(sm_id, prop, value, is_string=False):
    url = f"{BASE_URL}/submodels/{sm_id}/submodel-elements/{prop}/$value"

    payload = value if is_string else str(round(value, 4))

    r = requests.patch(url, json=payload)
    r.raise_for_status()

    print(f"  ✓ {prop} = {value}")


# -------------------------
# MAIN LOOP
# -------------------------
last_inputs = None

try:
    while True:
        current_inputs = {
            "RobotMoveTime": get_property(SM_INPUTS, "RobotMoveTime"),
            "PickPlaceTime": get_property(SM_INPUTS, "PickPlaceTime"),
            "QueueDelay": get_property(SM_INPUTS, "QueueDelay"),
            "AvailableTime": get_property(SM_INPUTS, "AvailableTime"),
        }

        # Only run when inputs change
        if current_inputs != last_inputs:
            print("\n--- Input change detected ---")
            print("Inputs used:")

            for k, v in current_inputs.items():
                print(f"  {k}: {v}")

            robot_move_time = current_inputs["RobotMoveTime"]
            pick_place_time = current_inputs["PickPlaceTime"]
            queue_delay     = current_inputs["QueueDelay"]
            available_time  = current_inputs["AvailableTime"]

            # KPIs
            cycle_time = robot_move_time + pick_place_time
            throughput = 60 / cycle_time
            utilization = (cycle_time / available_time) * 100
            production_lead_time = cycle_time + queue_delay

            # Output writes
            put_property(SM_RESULTS, "CycleTime", cycle_time)
            put_property(SM_RESULTS, "Throughput", throughput)
            put_property(SM_RESULTS, "Utilization", utilization)
            put_property(SM_RESULTS, "ProductionLeadTime", production_lead_time)

            ts = datetime.now(timezone.utc).isoformat()
            put_property(SM_MODEL, "LastUpdated", ts, is_string=True)

            print("\nResults:")
            print(f"  CycleTime = {cycle_time:.2f}s")
            print(f"  Throughput = {throughput:.2f}/min")
            print(f"  Utilization = {utilization:.2f}%")
            print(f"  LeadTime = {production_lead_time:.2f}s")

            last_inputs = current_inputs.copy()

        time.sleep(1)

except KeyboardInterrupt:
    print("\nSimulation stopped.")