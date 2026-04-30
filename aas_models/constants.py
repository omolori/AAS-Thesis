"""Identifiers, semantic IDs, and constants used throughout the UR3 AAS.

Centralizing these prevents typos across submodels and makes it easy to
change naming conventions in one spot.
"""
from __future__ import annotations

# -- Identifiers (URIs) -----------------------------------------------------
# Per IDTA Part 1, every Identifiable element (AAS, Submodel, Asset)
# needs a globally-unique IRI. We use a synthetic AAU domain.
BASE = "https://aau.dk/aas/ur3"

ASSET_ID                 = f"{BASE}/asset/UR3-001"
AAS_ID                   = f"{BASE}/shell/UR3-001"
SUBMODEL_NAMEPLATE_ID    = f"{BASE}/submodels/DigitalNameplate"
SUBMODEL_TECHNICAL_ID    = f"{BASE}/submodels/TechnicalData"
SUBMODEL_OPERATIONAL_ID  = f"{BASE}/submodels/OperationalData"
SUBMODEL_SIMULATION_ID   = f"{BASE}/submodels/SimulationModels"

# -- Semantic IDs ----------------------------------------------------------
# In a "real" deployment these would point to IDTA-published submodel
# template IRIs (e.g. https://admin-shell.io/zvei/nameplate/2/0/Nameplate)
# and ECLASS-IRDIs for individual properties. We use those where the IDTA
# defines them and synthetic IRIs for UR3-specific values.
SEM_NAMEPLATE_TEMPLATE   = "https://admin-shell.io/zvei/nameplate/2/0/Nameplate"
SEM_TECHDATA_TEMPLATE    = "https://admin-shell.io/ZVEI/TechnicalData/Submodel/1/2"

# UR3 datasheet values (Universal Robots, UR3e/UR3 specifications)
UR3_MANUFACTURER         = "Universal Robots A/S"
UR3_MODEL                = "UR3"
UR3_SERIAL_NUMBER        = "UR3-LAB-001"   # placeholder; lab can override
UR3_YEAR_OF_CONSTRUCTION = "2024"

# Mechanical / kinematic specs (from UR3 datasheet)
UR3_REACH_MM             = 500.0           # 500 mm working radius
UR3_PAYLOAD_KG           = 3.0             # 3 kg rated payload
UR3_DOF                  = 6               # 6 rotary joints
UR3_FOOTPRINT_MM         = 128.0           # base diameter
UR3_WEIGHT_KG            = 11.0
UR3_TCP_SPEED_MAX_MS     = 1.0             # 1 m/s rated TCP speed
UR3_REPEATABILITY_MM     = 0.1             # ±0.1 mm repeatability

# Per-joint limits (rad/s for velocity, ±rad for position)
# UR3 wrist joints (4,5,6) move faster than base/shoulder/elbow.
UR3_JOINT_VEL_LIMITS_RAD_S = [
    3.14, 3.14, 3.14,  # base, shoulder, elbow
    6.28, 6.28, 6.28,  # wrist 1, 2, 3
]
UR3_JOINT_POS_LIMITS_RAD = [6.28] * 6   # ±2π for all joints (effectively unlimited)
