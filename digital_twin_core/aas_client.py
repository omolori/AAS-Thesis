"""HTTP client for the local AAS server.

Fetches simulation parameters from the SimulationModels submodel and
presents them as plain Python dicts that sim_runner.py can consume
directly. Keeps all AAS JSON parsing contained here so the rest of
the pipeline never touches raw AAS API responses.

Maps to thesis §2.2 (Reactive AAS): the AAS server is the single
authoritative source for parameters injected into the AAS-enabled
simulation pipeline.
"""
from __future__ import annotations

import base64

import requests

from aas_models.constants import SUBMODEL_SIMULATION_ID


def _b64url(identifier: str) -> str:
    """URL-safe Base64, no padding -- the form the AAS Part 2 API expects."""
    return base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


def _index_by_id_short(elements: list[dict]) -> dict[str, dict]:
    """Build a {idShort: element} lookup from a submodelElements list."""
    return {el["idShort"]: el for el in elements}


def _prop_float(elements_index: dict[str, dict], id_short: str) -> float:
    """Extract a float Property value from an indexed element dict."""
    return float(elements_index[id_short]["value"])


class AASClient:
    """Thin client for the local AAS Part 2 REST API."""

    def __init__(self, base_url: str = "http://localhost:8080/api/v3.0") -> None:
        self.base_url = base_url.rstrip("/")

    def is_alive(self) -> bool:
        """Quick health check: GET /shells and verify at least one is loaded."""
        try:
            r = requests.get(f"{self.base_url}/shells", timeout=3)
            r.raise_for_status()
            data = r.json()
            shell_list = data.get("result", data) if isinstance(data, dict) else data
            return len(shell_list) > 0
        except Exception:
            return False

    def fetch_simulation_models(self) -> dict:
        """Fetch SimulationModels submodel and return structured parameters.

        Returns:
            {
                "payload": {"mass_kg": float, "cog": [x, y, z]},
                "tool_tcp": [x, y, z, rx, ry, rz],
                "joint_calibration_offsets_rad": [float]*6,
                "joint_friction_coefficients": [
                    {"coulomb_Nm": float, "viscous_Nm_s_rad": float},
                    ...  # 6 entries, one per joint
                ],
            }
        """
        url = f"{self.base_url}/submodels/{_b64url(SUBMODEL_SIMULATION_ID)}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        sm = r.json()

        top = _index_by_id_short(sm["submodelElements"])

        # --- Payload ---
        payload_els = _index_by_id_short(top["Payload"]["value"])
        payload = {
            "mass_kg": _prop_float(payload_els, "Mass_kg"),
            "cog": [
                _prop_float(payload_els, "CoG_X_m"),
                _prop_float(payload_els, "CoG_Y_m"),
                _prop_float(payload_els, "CoG_Z_m"),
            ],
        }

        # --- Tool TCP ---
        tcp_els = _index_by_id_short(top["ToolTCPOffset"]["value"])
        tool_tcp = [
            _prop_float(tcp_els, "X_m"),
            _prop_float(tcp_els, "Y_m"),
            _prop_float(tcp_els, "Z_m"),
            _prop_float(tcp_els, "Rx"),
            _prop_float(tcp_els, "Ry"),
            _prop_float(tcp_els, "Rz"),
        ]

        # --- Calibration offsets ---
        calib_els = _index_by_id_short(top["JointCalibrationOffsets_rad"]["value"])
        calibration_offsets = [
            _prop_float(calib_els, f"Joint{i}") for i in range(1, 7)
        ]

        # --- Friction coefficients ---
        friction_joints = top["JointFrictionCoefficients"]["value"]
        friction_coefficients = []
        for joint_col in sorted(friction_joints, key=lambda e: e["idShort"]):
            coeff_els = _index_by_id_short(joint_col["value"])
            friction_coefficients.append({
                "coulomb_Nm": _prop_float(coeff_els, "Coulomb_Nm"),
                "viscous_Nm_s_rad": _prop_float(coeff_els, "Viscous_Nm_s_rad"),
            })

        return {
            "payload": payload,
            "tool_tcp": tool_tcp,
            "joint_calibration_offsets_rad": calibration_offsets,
            "joint_friction_coefficients": friction_coefficients,
        }
