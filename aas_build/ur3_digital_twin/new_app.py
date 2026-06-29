from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import requests
import base64
import json

app = FastAPI()

BASE_URL = "http://localhost:8081"


# ------------------------------------------------
# BASE64 ENCODING
# ------------------------------------------------

def b64(id_str):
    return base64.urlsafe_b64encode(
        id_str.encode()
    ).decode().rstrip("=")


# ------------------------------------------------
# SUBMODEL IDS
# ------------------------------------------------

SM_COMMAND = b64("urn:ur3:motioncommand:1")

SM_DYNAMICS = b64("urn:ur3:dynamicsparameters:1")

SM_STATE = b64("urn:ur3:robotstate:1")

SM_KPIS = b64("urn:ur3:performancekpis:1")


# ------------------------------------------------
# READ ALL ELEMENTS
# ------------------------------------------------

def get_submodel_elements(sm_id):

    url = (
        f"{BASE_URL}/submodels/"
        f"{sm_id}/submodel-elements"
    )

    r = requests.get(url)

    r.raise_for_status()

    data = r.json()["result"]

    return {
        x["idShort"]: x["value"]
        for x in data
    }


# ------------------------------------------------
# UPDATE PROPERTY
# ------------------------------------------------

def update_property(sm_id, key, value):

    url = (
        f"{BASE_URL}/submodels/"
        f"{sm_id}/submodel-elements/"
        f"{key}/$value"
    )

    r = requests.patch(
        url,
        json=str(value)
    )

    r.raise_for_status()


# ------------------------------------------------
# GETTERS
# ------------------------------------------------

def get_inputs():

    return {
        "motion": get_submodel_elements(
            SM_COMMAND
        ),

        "dynamics": get_submodel_elements(
            SM_DYNAMICS
        )
    }


def get_state():

    return get_submodel_elements(
        SM_STATE
    )


def get_kpis():

    return get_submodel_elements(
        SM_KPIS
    )


# ------------------------------------------------
# INPUT MODEL
# ------------------------------------------------

class TwinInputs(BaseModel):

    TargetJointPositions: list[float]

    SpeedScaling: float

    PayloadMass: float

    FrictionCoefficient: float

    CurrentNoiseLevel: float

    ControlLatency: float

    DampingFactor: float


# ------------------------------------------------
# UPDATE INPUTS
# ------------------------------------------------

@app.post("/inputs")
def set_inputs(inputs: TwinInputs):

    # -------------------------
    # MotionCommand
    # -------------------------

    update_property(
        SM_COMMAND,
        "TargetJointPositions",
        json.dumps(inputs.TargetJointPositions)
    )

    update_property(
        SM_COMMAND,
        "SpeedScaling",
        inputs.SpeedScaling
    )

    update_property(
        SM_COMMAND,
        "PayloadMass",
        inputs.PayloadMass
    )

    # -------------------------
    # DynamicsParameters
    # -------------------------

    update_property(
        SM_DYNAMICS,
        "FrictionCoefficient",
        inputs.FrictionCoefficient
    )

    update_property(
        SM_DYNAMICS,
        "CurrentNoiseLevel",
        inputs.CurrentNoiseLevel
    )

    update_property(
        SM_DYNAMICS,
        "ControlLatency",
        inputs.ControlLatency
    )

    update_property(
        SM_DYNAMICS,
        "DampingFactor",
        inputs.DampingFactor
    )

    return {
        "status": "updated"
    }


# ------------------------------------------------
# DATA ENDPOINT
# ------------------------------------------------

@app.get("/data")
def data():

    return {

        "inputs": get_inputs(),

        "state": get_state(),

        "kpis": get_kpis()
    }


# ------------------------------------------------
# DASHBOARD UI
# ------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def ui():

    return """
<!DOCTYPE html>
<html>

<head>

<title>UR3 Digital Twin</title>

<style>

*{
  box-sizing:border-box;
  margin:0;
  padding:0;
}

body{
  font-family:system-ui,sans-serif;
  background:#f5f5f5;
  color:#111;
  padding:2rem;
}

.title{
  font-size:20px;
  font-weight:600;
}

.top-bar{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:2rem;
}

.live{
  font-size:12px;
  color:#666;
}

.section{
  margin-bottom:2rem;
}

.section-title{
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.08em;
  color:#777;
  margin-bottom:10px;
}

.grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:10px;
}

.card{
  background:white;
  border-radius:10px;
  padding:1rem;
  border:1px solid #e5e5e5;
}

.label{
  font-size:12px;
  color:#666;
  margin-bottom:5px;
}

.value{
  font-size:22px;
  font-weight:600;
}

.unit{
  font-size:11px;
  color:#999;
  margin-top:4px;
}

.inputs{
  background:white;
  padding:1.5rem;
  border-radius:12px;
  border:1px solid #e5e5e5;
}

.row{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
  margin-bottom:12px;
}

.group{
  display:flex;
  flex-direction:column;
  gap:6px;
}

.group label{
  font-size:12px;
  color:#666;
}

.group input{
  padding:8px 10px;
  border:1px solid #ddd;
  border-radius:6px;
}

button{
  margin-top:10px;
  padding:10px 16px;
  border:none;
  border-radius:8px;
  background:black;
  color:white;
  cursor:pointer;
}

button:hover{
  opacity:.9;
}

.status{
  margin-left:10px;
  font-size:12px;
  color:#777;
}

</style>

</head>

<body>

<div class="top-bar">

<div class="title">
UR3 Digital Twin
</div>

<div class="live">
● LIVE
</div>

</div>


<!-- KPIs -->

<div class="section">

<div class="section-title">
Performance KPIs
</div>

<div class="grid">

<div class="card">
<div class="label">Cycle Time</div>
<div class="value" id="cycle">—</div>
<div class="unit">seconds</div>
</div>

<div class="card">
<div class="label">RMS Current</div>
<div class="value" id="rms">—</div>
<div class="unit">amps</div>
</div>

<div class="card">
<div class="label">Energy Consumption</div>
<div class="value" id="energy">—</div>
<div class="unit">joules</div>
</div>

<div class="card">
<div class="label">Position Error</div>
<div class="value" id="error">—</div>
<div class="unit">meters</div>
</div>

</div>

</div>


<!-- ROBOT STATE -->

<div class="section">

<div class="section-title">
Robot State
</div>

<div class="grid">

<div class="card">
<div class="label">Joint Positions</div>
<div class="value" style="font-size:13px" id="joints">—</div>
</div>

<div class="card">
<div class="label">Joint Currents</div>
<div class="value" style="font-size:13px" id="currents">—</div>
</div>

<div class="card">
<div class="label">TCP Pose</div>
<div class="value" style="font-size:13px" id="tcp">—</div>
</div>

</div>

</div>


<!-- INPUTS -->

<div class="section">

<div class="section-title">
Simulation Inputs
</div>

<div class="inputs">

<div class="row">

<div class="group">
<label>Target Joint Positions</label>
<input id="jpos"
value="[0,-1.57,1.2,-1.57,-1.57,0]">
</div>

<div class="group">
<label>Speed Scaling</label>
<input id="speed" type="number" step="0.1">
</div>

</div>

<div class="row">

<div class="group">
<label>Payload Mass (kg)</label>
<input id="payload" type="number" step="0.1">
</div>

<div class="group">
<label>Friction Coefficient</label>
<input id="friction" type="number" step="0.01">
</div>

</div>

<div class="row">

<div class="group">
<label>Current Noise Level</label>
<input id="noise" type="number" step="0.01">
</div>

<div class="group">
<label>Control Latency (s)</label>
<input id="latency" type="number" step="0.01">
</div>

</div>

<div class="row">

<div class="group">
<label>Damping Factor</label>
<input id="damping" type="number" step="0.01">
</div>

</div>

<button onclick="updateInputs()">
Update Simulation
</button>

<span class="status" id="status"></span>

</div>

</div>


<script>

let inputsLoaded = false;


// ------------------------------------------------
// LOAD DATA
// ------------------------------------------------

async function load(){

  try{

    const res = await fetch("/data");

    const data = await res.json();

    const k = data.kpis;

    const s = data.state;

    const i = data.inputs;


    // ------------------------------------------------
    // KPI UPDATES
    // ------------------------------------------------

    document.getElementById("cycle").textContent =
      k.CycleTime ? parseFloat(k.CycleTime).toFixed(2) : "—";

    document.getElementById("rms").textContent =
      k.RMSCurrent ? parseFloat(k.RMSCurrent).toFixed(3) : "—";

    document.getElementById("energy").textContent =
      k.EnergyConsumption ? parseFloat(k.EnergyConsumption).toFixed(2) : "—";

    document.getElementById("error").textContent =
      k.PositionError ? parseFloat(k.PositionError).toFixed(4) : "—";


    // ------------------------------------------------
    // ROBOT STATE UPDATES
    // ------------------------------------------------

    document.getElementById("joints").textContent =
      s.JointPositions || "—";

    document.getElementById("currents").textContent =
      s.JointCurrents || "—";

    document.getElementById("tcp").textContent =
      s.TCP_Pose || "—";


    // ------------------------------------------------
    // INPUTS
    // ONLY LOAD ONCE
    // ------------------------------------------------

    if (!inputsLoaded){

      document.getElementById("jpos").value =
        i.motion.TargetJointPositions;

      document.getElementById("speed").value =
        i.motion.SpeedScaling;

      document.getElementById("payload").value =
        i.motion.PayloadMass;

      document.getElementById("friction").value =
        i.dynamics.FrictionCoefficient;

      document.getElementById("noise").value =
        i.dynamics.CurrentNoiseLevel;

      document.getElementById("latency").value =
        i.dynamics.ControlLatency;

      document.getElementById("damping").value =
        i.dynamics.DampingFactor;

      inputsLoaded = true;
    }

  } catch(e){

    console.log(e);

  }

}


// ------------------------------------------------
// UPDATE INPUTS
// ------------------------------------------------

async function updateInputs(){

  const status =
    document.getElementById("status");

  status.textContent = "Updating...";

  try{

    await fetch("/inputs", {

      method:"POST",

      headers:{
        "Content-Type":"application/json"
      },

      body:JSON.stringify({

        TargetJointPositions:
          JSON.parse(
            document.getElementById("jpos").value
          ),

        SpeedScaling:
          parseFloat(
            document.getElementById("speed").value
          ),

        PayloadMass:
          parseFloat(
            document.getElementById("payload").value
          ),

        FrictionCoefficient:
          parseFloat(
            document.getElementById("friction").value
          ),

        CurrentNoiseLevel:
          parseFloat(
            document.getElementById("noise").value
          ),

        ControlLatency:
          parseFloat(
            document.getElementById("latency").value
          ),

        DampingFactor:
          parseFloat(
            document.getElementById("damping").value
          )

      })

    });

    status.textContent = "Updated";

    // wait for simulation recalculation
    setTimeout(load, 1500);

    setTimeout(() => {

      status.textContent = "";

    }, 2000);

  } catch(e){

    console.log(e);

    status.textContent = "Failed";

  }

}


// ------------------------------------------------
// AUTO REFRESH
// ------------------------------------------------

setInterval(load, 1000);

load();

</script>

</body>
</html>
"""