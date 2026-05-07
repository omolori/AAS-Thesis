"""Simulation Models submodel.

Parameters are loaded from data/sim_params.json at build time so they
can be edited via the dashboard without touching source code.
"""
from __future__ import annotations
from pathlib import Path

from basyx.aas import model

from aas_models.constants import SUBMODEL_SIMULATION_ID
from aas_models._helpers import make_collection, make_property

_PARAMS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sim_params.json"


def build_simulation_models() -> model.Submodel:
    from digital_twin_core.sim_params import load
    p = load(_PARAMS_PATH)

    submodel = model.Submodel(
        id_=SUBMODEL_SIMULATION_ID,
        id_short="SimulationModels",
    )

    payload = make_collection(
        id_short="Payload",
        description="Mass and centre-of-gravity of the load attached to the TCP.",
        elements=[
            make_property("Mass_kg",  p["payload"]["mass_kg"],  model.datatypes.Double),
            make_property("CoG_X_m",  p["payload"]["cog_x_m"],  model.datatypes.Double),
            make_property("CoG_Y_m",  p["payload"]["cog_y_m"],  model.datatypes.Double),
            make_property("CoG_Z_m",  p["payload"]["cog_z_m"],  model.datatypes.Double),
        ],
    )
    submodel.submodel_element.add(payload)

    tcp = p["tool_tcp"]
    tool_tcp = make_collection(
        id_short="ToolTCPOffset",
        description="Tool centre point pose relative to flange (x,y,z in m; rx,ry,rz axis-angle rad).",
        elements=[
            make_property("X_m", tcp["x_m"], model.datatypes.Double),
            make_property("Y_m", tcp["y_m"], model.datatypes.Double),
            make_property("Z_m", tcp["z_m"], model.datatypes.Double),
            make_property("Rx",  tcp["rx"],  model.datatypes.Double),
            make_property("Ry",  tcp["ry"],  model.datatypes.Double),
            make_property("Rz",  tcp["rz"],  model.datatypes.Double),
        ],
    )
    submodel.submodel_element.add(tool_tcp)

    calib = model.SubmodelElementCollection(
        id_short="JointCalibrationOffsets_rad",
        description=model.MultiLanguageTextType({
            "en": "Per-joint calibration offsets in rad (delta from nominal kinematics).",
        }),
    )
    for i, val in enumerate(p["joint_calibration_offsets_rad"], 1):
        calib.value.add(make_property(f"Joint{i}", float(val), model.datatypes.Double))
    submodel.submodel_element.add(calib)

    friction = model.SubmodelElementCollection(
        id_short="JointFrictionCoefficients",
        description=model.MultiLanguageTextType({
            "en": "Per-joint Coulomb (a) and viscous (b) friction coefficients.",
        }),
    )
    for i, coeff in enumerate(p["joint_friction_coefficients"], 1):
        friction.value.add(make_collection(
            id_short=f"Joint{i}",
            elements=[
                make_property("Coulomb_Nm",      float(coeff["coulomb_Nm"]),      model.datatypes.Double),
                make_property("Viscous_Nm_s_rad", float(coeff["viscous_Nm_s_rad"]), model.datatypes.Double),
            ],
        ))
    submodel.submodel_element.add(friction)

    return submodel
