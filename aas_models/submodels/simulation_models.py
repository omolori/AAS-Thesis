"""Simulation Models submodel.

Maps to the 'Behavioral model' + 'Rule model' DT-classes in the thesis
Table 2.1. Contains the parameters that the AAS-enabled simulation pipeline
will inject into URSim BEFORE running a task -- the values URSim's defaults
do *not* know about, but that the AAS does.

These are the "asset properties that impact production output" you cite in
Section 2.3 (Simulation-Specific AAS Use Cases): payload, tool TCP offset,
joint friction, calibration offsets. By feeding these into URSim, the
AAS-enabled run is hypothesized to track the real UR3 more closely than
URSim's default simulation does.
"""
from __future__ import annotations

from basyx.aas import model

from aas_models.constants import SUBMODEL_SIMULATION_ID
from aas_models._helpers import make_collection, make_property


def build_simulation_models() -> model.Submodel:
    submodel = model.Submodel(
        id_=SUBMODEL_SIMULATION_ID,
        id_short="SimulationModels",
    )

    # ----- Payload --------------------------------------------------------
    # The current load attached to the TCP. Affects gravity compensation
    # and dynamics. URSim defaults to 0 kg unless told otherwise.
    # Representative values for a small gripper (0.5 kg, CoG 6 cm along
    # flange Z axis). Replace with lab-measured values once available.
    payload = make_collection(
        id_short="Payload",
        description="Mass and centre-of-gravity of the load attached to the TCP.",
        elements=[
            make_property("Mass_kg",  0.5,  model.datatypes.Double),
            make_property("CoG_X_m",  0.0,  model.datatypes.Double),
            make_property("CoG_Y_m",  0.0,  model.datatypes.Double),
            make_property("CoG_Z_m",  0.06, model.datatypes.Double),
        ],
    )
    submodel.submodel_element.add(payload)

    # ----- Tool TCP offset ------------------------------------------------
    # Position + orientation of the tool tip relative to the flange.
    # Critical for accurate Cartesian motion in simulation.
    # Tool extends 10 cm along flange Z axis, no rotation offset.
    # Replace with PolyScope 4-point TCP wizard result from the lab.
    tool_tcp = make_collection(
        id_short="ToolTCPOffset",
        description="Tool centre point pose relative to flange (x,y,z in m; rx,ry,rz axis-angle rad).",
        elements=[
            make_property("X_m", 0.0, model.datatypes.Double),
            make_property("Y_m", 0.0, model.datatypes.Double),
            make_property("Z_m", 0.1, model.datatypes.Double),
            make_property("Rx",  0.0, model.datatypes.Double),
            make_property("Ry",  0.0, model.datatypes.Double),
            make_property("Rz",  0.0, model.datatypes.Double),
        ],
    )
    submodel.submodel_element.add(tool_tcp)

    # ----- Per-joint calibration offsets ----------------------------------
    # Real robots have calibration deltas vs the nominal kinematics. URSim
    # defaults to a perfect robot; feeding these offsets into the simulation
    # makes it match the physical UR3 more closely.
    calib = model.SubmodelElementCollection(
        id_short="JointCalibrationOffsets_rad",
        description=model.MultiLanguageTextType({
            "en": "Per-joint calibration offsets in rad (delta from nominal kinematics).",
        }),
    )
    for i in range(1, 7):
        calib.value.add(make_property(f"Joint{i}", 0.0, model.datatypes.Double))
    submodel.submodel_element.add(calib)

    # ----- Per-joint friction coefficients --------------------------------
    # Simple Coulomb + viscous model: tau_friction = a * sign(qd) + b * qd
    # URSim's default frictionless model is a known source of sim-vs-real
    # divergence; including these is one of the AAS's added-value claims.
    friction = model.SubmodelElementCollection(
        id_short="JointFrictionCoefficients",
        description=model.MultiLanguageTextType({
            "en": "Per-joint Coulomb (a) and viscous (b) friction coefficients.",
        }),
    )
    for i in range(1, 7):
        friction.value.add(make_collection(
            id_short=f"Joint{i}",
            elements=[
                make_property("Coulomb_Nm",     0.0, model.datatypes.Double),
                make_property("Viscous_Nm_s_rad", 0.0, model.datatypes.Double),
            ],
        ))
    submodel.submodel_element.add(friction)

    return submodel
