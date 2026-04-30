"""Technical Data submodel.

Maps to the 'Geometric model' + 'Physical model' DT-classes in the thesis
Table 2.1. Contains the static, datasheet-level facts about the UR3:
reach, payload, joint limits, etc.

This data is what the AAS-enabled simulation pipeline will use to
parameterize URSim (instead of relying on URSim's defaults).
"""
from __future__ import annotations

from basyx.aas import model

from aas_models.constants import (
    SEM_TECHDATA_TEMPLATE,
    SUBMODEL_TECHNICAL_ID,
    UR3_DOF,
    UR3_FOOTPRINT_MM,
    UR3_JOINT_VEL_LIMITS_RAD_S,
    UR3_PAYLOAD_KG,
    UR3_REACH_MM,
    UR3_REPEATABILITY_MM,
    UR3_TCP_SPEED_MAX_MS,
    UR3_WEIGHT_KG,
)
from aas_models._helpers import make_collection, make_property


def build_technical_data() -> model.Submodel:
    submodel = model.Submodel(
        id_=SUBMODEL_TECHNICAL_ID,
        id_short="TechnicalData",
        semantic_id=model.ExternalReference((
            model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value=SEM_TECHDATA_TEMPLATE,
            ),
        )),
    )

    # ----- Mechanical properties -------------------------------------------
    mechanical = make_collection(
        id_short="MechanicalProperties",
        description="Physical and mechanical specifications of the UR3.",
        elements=[
            make_property("Reach_mm",         UR3_REACH_MM,         model.datatypes.Double),
            make_property("PayloadMax_kg",    UR3_PAYLOAD_KG,       model.datatypes.Double),
            make_property("Weight_kg",        UR3_WEIGHT_KG,        model.datatypes.Double),
            make_property("FootprintDiameter_mm", UR3_FOOTPRINT_MM, model.datatypes.Double),
            make_property("Repeatability_mm", UR3_REPEATABILITY_MM, model.datatypes.Double),
            make_property("TCPSpeedMax_m_s",  UR3_TCP_SPEED_MAX_MS, model.datatypes.Double),
            make_property("DegreesOfFreedom", UR3_DOF,              model.datatypes.Int),
        ],
    )
    submodel.submodel_element.add(mechanical)

    # ----- Per-joint velocity limits --------------------------------------
    # Each joint has its own max velocity. Stored as a SubmodelElementCollection
    # so the simulator can iterate over them.
    joints_coll = model.SubmodelElementCollection(
        id_short="JointVelocityLimits_rad_s",
        description=model.MultiLanguageTextType({
            "en": "Maximum angular velocity per joint, in rad/s.",
        }),
    )
    for i, vel in enumerate(UR3_JOINT_VEL_LIMITS_RAD_S, start=1):
        joints_coll.value.add(make_property(
            id_short=f"Joint{i}_VelMax",
            value=vel,
            value_type=model.datatypes.Double,
        ))
    submodel.submodel_element.add(joints_coll)

    return submodel
