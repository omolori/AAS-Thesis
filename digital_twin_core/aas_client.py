"""HTTP clients for AAS servers.

AASClient    — local basyx-python-sdk server (Phase 3/4 local server).
BaSyxClient  — external BaSyx AAS Environment server (Phase 4+ BaSyx deployment).
               Supports both local IP and ngrok tunnel.
               Reads SimulationInputs before a run and writes KPIResults after.

Maps to thesis §2.2 (Reactive AAS): bidirectional AAS integration where the
server both configures the simulation (input) and receives the results (output).
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


class BaSyxClient:
    """Client for the external BaSyx AAS Environment server.

    Reads simulation input parameters from the SimulationInputs submodel
    and writes computed KPIs back to the KPIResults submodel after each run.

    Works with both the local IP and a public ngrok tunnel.  When using
    ngrok, the 'ngrok-skip-browser-warning' header is required to bypass
    the ngrok interstitial page.

    Property mapping:
        SimulationInputs:
            RobotMoveTime   → trajectory speed_rad_s  (rad/s)
            PickPlaceTime   → dwell time at pick/place (s)
            QueueDelay      → pause between cycles (s)
            AvailableTime   → shift available time for Utilization KPI (s)

        KPIResults (written after each run):
            CycleTime           → mean cycle time (s)
            Throughput          → cycles per hour
            Utilization         → motion time / AvailableTime  (%)
            ProductionLeadTime  → total run duration (s)
    """

    def __init__(
        self,
        base_url: str,
        inputs_id: str,
        kpi_id: str,
        use_ngrok_header: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.inputs_id = inputs_id
        self.kpi_id = kpi_id
        self._headers: dict[str, str] = {}
        if use_ngrok_header:
            self._headers["ngrok-skip-browser-warning"] = "true"

    def is_alive(self) -> bool:
        """Health check: try /submodels then /shells — works with different BaSyx versions."""
        for endpoint in ["/submodels", "/shells"]:
            try:
                r = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self._headers,
                    timeout=5,
                )
                if r.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    def fetch_simulation_inputs(self) -> dict:
        """Read SimulationInputs submodel and return trajectory parameters.

        Returns:
            {
                "robot_move_time":  float,  # speed_rad_s for moveJ
                "pick_place_time":  float,  # dwell_s at pick and place
                "queue_delay":      float,  # pause between cycles (s)
                "available_time":   float,  # shift available time (s)
            }
        """
        def _get(prop: str) -> float:
            url = (
                f"{self.base_url}/submodels/{_b64url(self.inputs_id)}"
                f"/submodel-elements/{prop}"
            )
            r = requests.get(url, headers=self._headers, timeout=5)
            r.raise_for_status()
            return float(r.json()["value"])

        return {
            "robot_move_time": _get("RobotMoveTime"),
            "pick_place_time": _get("PickPlaceTime"),
            "queue_delay":     _get("QueueDelay"),
            "available_time":  _get("AvailableTime"),
        }

    def write_kpi_results(
        self,
        cycle_time_s: float,
        throughput_per_hour: float,
        utilization_pct: float,
        production_lead_time_s: float,
    ) -> None:
        """PATCH KPIResults submodel with computed values."""
        kpis = {
            "CycleTime":           cycle_time_s,
            "Throughput":          throughput_per_hour,
            "Utilization":         utilization_pct,
            "ProductionLeadTime":  production_lead_time_s,
        }
        for prop, value in kpis.items():
            url = (
                f"{self.base_url}/submodels/{_b64url(self.kpi_id)}"
                f"/submodel-elements/{prop}/$value"
            )
            r = requests.patch(
                url,
                json=value,
                headers={**self._headers, "Content-Type": "application/json"},
                timeout=5,
            )
            r.raise_for_status()
