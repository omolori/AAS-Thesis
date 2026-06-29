from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import base64

app = FastAPI()

BASE_URL = "http://localhost:8081"

def b64(id_str):
    return base64.urlsafe_b64encode(id_str.encode()).decode().rstrip("=")

SM_INPUTS  = b64("urn:ur3:simulationinputs:1")
SM_RESULTS = b64("urn:ur3:kpiresults:1")

def get_kpis():
    url = f"{BASE_URL}/submodels/{SM_RESULTS}/submodel-elements"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()["result"]
    return {x["idShort"]: x["value"] for x in data}

def get_inputs():
    url = f"{BASE_URL}/submodels/{SM_INPUTS}/submodel-elements"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()["result"]
    return {x["idShort"]: x["value"] for x in data}

def update_input(sm_id, key, value):
    url = f"{BASE_URL}/submodels/{sm_id}/submodel-elements/{key}/$value"
    r = requests.patch(url, json=str(value))
    r.raise_for_status()

class Inputs(BaseModel):
    RobotMoveTime: float
    PickPlaceTime: float
    QueueDelay: float
    AvailableTime: float

@app.post("/inputs")
def set_inputs(inputs: Inputs):
    update_input(SM_INPUTS, "RobotMoveTime", inputs.RobotMoveTime)
    update_input(SM_INPUTS, "PickPlaceTime", inputs.PickPlaceTime)
    update_input(SM_INPUTS, "QueueDelay", inputs.QueueDelay)
    update_input(SM_INPUTS, "AvailableTime", inputs.AvailableTime)
    return {"status": "updated"}

@app.get("/data")
def data():
    return {
        "inputs": get_inputs(),
        "kpis": get_kpis()
    }

@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>UR3 Digital Twin</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #111; padding: 2rem; }
    .title { font-size: 18px; font-weight: 500; margin-bottom: 1.5rem; }
    .section-label { font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: #888; margin-bottom: 10px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 2rem; }
    .kpi-card { background: #ececec; border-radius: 8px; padding: 1rem; }
    .kpi-label { font-size: 12px; color: #666; margin-bottom: 6px; }
    .kpi-value { font-size: 22px; font-weight: 500; }
    .kpi-unit { font-size: 12px; color: #999; margin-top: 2px; }
    .inputs-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem; }
    .input-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .input-group { display: flex; flex-direction: column; gap: 6px; }
    .input-group label { font-size: 12px; color: #666; }
    .input-group input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
    .btn-row { display: flex; align-items: center; gap: 12px; margin-top: 4px; }
    button { padding: 8px 18px; border: 1px solid #ccc; border-radius: 6px; background: #fff; font-size: 14px; cursor: pointer; }
    button:hover { background: #f0f0f0; }
    .status { font-size: 12px; color: #999; }
    .status.ok { color: #2a7a2a; }
    .status.err { color: #c0392b; }
    .top-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
    .pulse { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #2a7a2a; margin-right: 6px; animation: pulse 2s infinite; vertical-align: middle; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
    .live-badge { font-size: 12px; color: #888; display: flex; align-items: center; }
  </style>
</head>
<body>
  <div class="top-bar">
    <span class="title">UR3 Digital Twin</span>
    <span class="live-badge"><span class="pulse"></span>Live</span>
  </div>

  <p class="section-label">KPIs</p>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Cycle time</div>
      <div class="kpi-value" id="k-cycle">—</div>
      <div class="kpi-unit">seconds</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Throughput</div>
      <div class="kpi-value" id="k-throughput">—</div>
      <div class="kpi-unit">parts / min</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Utilization</div>
      <div class="kpi-value" id="k-util">—</div>
      <div class="kpi-unit">percent</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Lead time</div>
      <div class="kpi-value" id="k-lead">—</div>
      <div class="kpi-unit">seconds</div>
    </div>
  </div>

  <p class="section-label">Simulation inputs</p>
  <div class="inputs-card">
    <div class="input-row">
      <div class="input-group">
        <label for="rmt">Robot move time (s)</label>
        <input type="number" id="rmt" step="0.1">
      </div>
      <div class="input-group">
        <label for="ppt">Pick & place time (s)</label>
        <input type="number" id="ppt" step="0.1">
      </div>
    </div>
    <div class="input-row">
      <div class="input-group">
        <label for="qd">Queue delay (s)</label>
        <input type="number" id="qd" step="0.1">
      </div>
      <div class="input-group">
        <label for="at">Available time (s)</label>
        <input type="number" id="at" step="0.1">
      </div>
    </div>
    <div class="btn-row">
      <button onclick="updateInputs()">Update inputs</button>
      <span class="status" id="status"></span>
    </div>
  </div>

<script>
let inputsLoaded = false;
let userEditing = false;
let editTimer = null;

["rmt","ppt","qd","at"].forEach(id => {
  document.getElementById(id).addEventListener("focus", () => {
    userEditing = true;
    clearTimeout(editTimer);
  });
  document.getElementById(id).addEventListener("blur", () => {
    editTimer = setTimeout(() => { userEditing = false; }, 3000);
  });
});

async function load() {
  try {
    const res = await fetch("/data");
    const data = await res.json();
    const k = data.kpis;
    const i = data.inputs;

    document.getElementById("k-cycle").textContent      = k.CycleTime           ? parseFloat(k.CycleTime).toFixed(1)           : "—";
    document.getElementById("k-throughput").textContent = k.Throughput           ? parseFloat(k.Throughput).toFixed(3)           : "—";
    document.getElementById("k-util").textContent       = k.Utilization          ? parseFloat(k.Utilization).toFixed(1)          : "—";
    document.getElementById("k-lead").textContent       = k.ProductionLeadTime   ? parseFloat(k.ProductionLeadTime).toFixed(1)   : "—";

    if (!inputsLoaded) {
      document.getElementById("rmt").value = i.RobotMoveTime;
      document.getElementById("ppt").value = i.PickPlaceTime;
      document.getElementById("qd").value  = i.QueueDelay;
      document.getElementById("at").value  = i.AvailableTime;
      inputsLoaded = true;
    }
  } catch(e) {}
}

async function updateInputs() {
  const status = document.getElementById("status");
  status.textContent = "Updating…";
  status.className = "status";
  userEditing = false;
  try {
    await fetch("/inputs", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        RobotMoveTime: parseFloat(document.getElementById("rmt").value),
        PickPlaceTime: parseFloat(document.getElementById("ppt").value),
        QueueDelay:    parseFloat(document.getElementById("qd").value),
        AvailableTime: parseFloat(document.getElementById("at").value)
      })
    });
    status.textContent = "Updated";
    status.className = "status ok";
    setTimeout(() => { status.textContent = ""; }, 2000);
    load();
  } catch(e) {
    status.textContent = "Failed";
    status.className = "status err";
  }
}

setInterval(load, 500);
load();
</script>
</body>
</html>
"""