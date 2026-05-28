# AAS-UR3 Digital Twin

Implementation of an Asset Administration Shell (AAS) based digital twin pipeline for a Universal Robots UR3 collaborative arm, developed as part of a Master's thesis at Aalborg University in collaboration with Danfoss.

The project investigates whether AAS-structured parameters improve the fidelity of kinematic robot simulations compared to conventional, manually configured approaches.

## What it does

Three execution pipelines are compared under identical conditions:

1. **Pipeline 1 — Real UR3**: physical robot, joint trajectories recorded via RTDE at 125 Hz
2. **Pipeline 2 — URSim (no AAS)**: URSim with manually assigned payload and TCP parameters
3. **Pipeline 3 — URSim (AAS)**: URSim parameterized at runtime from the AAS submodels via BaSyx REST API

A Streamlit web application provides monitoring, run inspection, cross-pipeline comparison, and AAS parameter editing.

## Architecture

```
aas_models/          AAS construction and submodel definitions
data_acquisition/    RTDE client for robot communication
digital_twin_core/   Pipeline execution, comparison, and analysis
dashboard/           Streamlit web application
scripts/             Entry points for running pipelines
config/              Central configuration
data/                SQLite database and AAS JSON storage
```

## Prerequisites

- Python 3.10+
- [URSim](https://www.universal-robots.com/download/software-e-series/simulator-non-linux/offline-simulator-e-series-ur-sim-for-non-linux-5921/) — Universal Robots offline simulator, runs as a virtual machine image (VMware or VirtualBox)
- [Docker](https://www.docker.com/) — required to run the Eclipse BaSyx AAS server for Pipeline 3
- Physical UR3 in remote control mode — required for Pipeline 1 only

## Setup

**1. Install Python dependencies**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure settings**

Edit `config/settings.toml`:

```toml
[ursim]
host = "192.168.x.x"      # IP of your URSim VM (run ifconfig inside URSim to find it)

[real_robot]
host = "192.168.x.x"      # IP of the physical UR3 (only needed for Pipeline 1)

[basyx_server]
local_url = "http://localhost:8081"   # BaSyx server address (see step 4)
use_ngrok = false                     # set true only if accessing BaSyx remotely
```

**3. Configure database**

For local use, the SQLite database (`data/runs.db`) is used automatically — no configuration needed.

For cloud storage (Supabase), copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your database URL.

**4. Start the BaSyx AAS server (Pipeline 3 only)**

Pipeline 3 requires the Eclipse BaSyx AAS server running in Docker:

```bash
docker run -p 8081:8081 eclipsebasyx/aas-environment:2.0.0-milestone-03
```

Upload the AASX package file to the server using the AASX Package Explorer or the BaSyx web interface.

**5. Verify connections**

```bash
python scripts/test_rtde_connection.py    # check URSim RTDE
python scripts/test_aas_server.py         # check local AAS server
```

## Running

**Start the local AAS server** (used by all pipelines):

```bash
python scripts/start_aas_server.py
```

This starts a lightweight Python AAS HTTP server on port 8080. Leave it running.

**Run a pipeline:**

```bash
python scripts/run_sim_no_aas.py   # Pipeline 2 — URSim, no AAS
python scripts/run_sim_aas.py      # Pipeline 3 — URSim with AAS parameters
python scripts/run_real.py         # Pipeline 1 — physical robot
```

**Launch the dashboard:**

```bash
streamlit run dashboard/Home.py
```

The dashboard opens at `http://localhost:8501`. It reads from the local SQLite database by default.

## Notes

- Pipelines 2 and 3 require URSim to be running and in remote control mode before execution.
- Pipeline 1 requires the physical UR3 to be in remote control mode and reachable on the configured IP.
- The `data/runs.db` file included in the repository contains sample run data for dashboard exploration without running any pipelines.
- AAS simulation parameters can be edited live from the dashboard under the AAS Parameters page.
