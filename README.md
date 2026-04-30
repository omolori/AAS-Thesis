# AAS-UR3 Digital Twin

Master's thesis implementation: investigating whether Asset Administration Shell (AAS) data improves the accuracy of UR3 robot simulations vs. traditional simulation methods.

## What this does

Three pipelines are run on the same UR3 task and their outputs are compared:

1. **Real UR3** — physical robot, joint trajectories recorded via RTDE.
2. **URSim (non-AAS)** — URSim with default parameters.
3. **URSim (AAS-enabled)** — URSim parameterized from AAS submodel data (calibration offsets, payload, friction model, tool offset, etc.).

The Digital Twin Core compares the three datasets and the Streamlit UI visualizes the differences (RMSE on joint positions, cycle time deltas, TCP path deviation).

## Architecture

Maps directly to the C4 container diagram in the thesis (Section 3.2):

```
data_acquisition/   -> Data Acquisition Service
aas_models/         -> AAS Service (modeling)
                       (server is the basyx-python-sdk WSGI app)
digital_twin_core/  -> Digital Twin Core
ui/                 -> User Interface
data/               -> SQLite + AAS JSON files
```

## Setup (Windows host, URSim in VMware)

1. Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Edit `config/settings.toml` and set `ursim.host` to your URSim VM's IP.

## Phase 2 — RTDE smoke test

With URSim running, in one terminal:
```
python scripts\test_rtde_connection.py
```
You should see 5 seconds of joint angles printed at ~10 Hz.

## Phase 3 — AAS server

Two terminals.

**Terminal 1** — start the AAS HTTP server (leave running):
```
python scripts\start_aas_server.py
```
The server is reachable at http://localhost:8080/api/v3.0/

**Terminal 2** — query the server:
```
python scripts\test_aas_server.py
```
You should see a list of one AAS, four submodels, and the contents of
the Digital Nameplate and Operational Data submodels printed as JSON.

## Repo layout

```
aas-ur3-thesis/
├── config/settings.toml           # central config
├── aas_models/                    # AAS construction + submodels
│   ├── ur3_aas_builder.py
│   └── submodels/
├── data_acquisition/              # RTDE client + recorder
│   ├── rtde_client.py
│   └── recorder.py
├── digital_twin_core/             # comparison & analysis
│   ├── aas_client.py
│   ├── sim_runner.py
│   └── comparator.py
├── ui/dashboard.py                # Streamlit app
├── scripts/                       # entry points
│   ├── test_rtde_connection.py
│   ├── start_aas_server.py
│   ├── run_real.py
│   ├── run_sim_no_aas.py
│   ├── run_sim_aas.py
│   └── compare_runs.py
└── data/                          # runs.db + aas storage
```
