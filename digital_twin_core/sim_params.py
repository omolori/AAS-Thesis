"""Read and write simulation parameters from/to data/sim_params.json.

The AAS server reads this file at startup to populate the SimulationModels
submodel. The dashboard edits this file and restarts the server to apply.
"""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULTS = {
    "motion_command": {
        "target_joint_positions": [0.0, -1.57, 1.2, -1.57, -1.57, 0.0],
        "speed_scaling": 0.8,
    },
    "dynamics": {
        "friction_coefficient": 0.12,
        "current_noise_level": 0.08,
        "control_latency_s": 0.03,
        "damping_factor": 0.15,
    },
    "payload": {
        "mass_kg":  0.5,
        "cog_x_m":  0.0,
        "cog_y_m":  0.0,
        "cog_z_m":  0.06,
    },
    "tool_tcp": {
        "x_m": 0.0,
        "y_m": 0.0,
        "z_m": 0.1,
        "rx":  0.0,
        "ry":  0.0,
        "rz":  0.0,
    },
    "joint_calibration_offsets_rad": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "joint_friction_coefficients": [
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
        {"coulomb_Nm": 0.0, "viscous_Nm_s_rad": 0.0},
    ],
}


def load(params_path: Path) -> dict:
    """Load params from JSON, falling back to defaults for missing keys."""
    if not params_path.exists():
        return _DEFAULTS.copy()
    with open(params_path) as f:
        data = json.load(f)
    # Merge with defaults so new keys added in future versions appear
    result = _DEFAULTS.copy()
    result.update(data)
    return result


def save(params_path: Path, params: dict) -> None:
    """Write params to JSON."""
    params_path.parent.mkdir(parents=True, exist_ok=True)
    with open(params_path, "w") as f:
        json.dump(params, f, indent=2)
