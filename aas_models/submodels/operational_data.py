"""Operational Data submodel.

Maps to the 'Behavioral model' DT-class in the thesis Table 2.1. Contains
live values describing the current state of the UR3:
- Joint positions, velocities (per joint)
- TCP pose, TCP speed
- Joint currents
- Runtime state (idle/playing/paused)
- Last update timestamp

This file *defines the structure* of the submodel and initializes it with
zeros / placeholders. In Phase 4, the Data Acquisition Service will update
these values from RTDE samples, making this a live, reactive submodel.
"""
from __future__ import annotations

from basyx.aas import model

from aas_models.constants import SUBMODEL_OPERATIONAL_ID
from aas_models._helpers import make_collection, make_property


def build_operational_data() -> model.Submodel:
    submodel = model.Submodel(
        id_=SUBMODEL_OPERATIONAL_ID,
        id_short="OperationalData",
    )

    # Per-joint position, velocity, and current. Each joint is a sub-collection.
    joint_positions = model.SubmodelElementCollection(
        id_short="JointPositions_rad",
        description=model.MultiLanguageTextType({
            "en": "Live joint angles in radians (q[0]..q[5]).",
        }),
    )
    joint_velocities = model.SubmodelElementCollection(
        id_short="JointVelocities_rad_s",
    )
    joint_currents = model.SubmodelElementCollection(
        id_short="JointCurrents_A",
    )

    for i in range(1, 7):
        joint_positions.value.add(make_property(f"Joint{i}", 0.0, model.datatypes.Double))
        joint_velocities.value.add(make_property(f"Joint{i}", 0.0, model.datatypes.Double))
        joint_currents.value.add(make_property(f"Joint{i}", 0.0, model.datatypes.Double))

    submodel.submodel_element.add(joint_positions)
    submodel.submodel_element.add(joint_velocities)
    submodel.submodel_element.add(joint_currents)

    # TCP pose: [x, y, z, rx, ry, rz] (axis-angle) in meters and radians
    tcp_pose = make_collection(
        id_short="TCPPose",
        description="Tool Center Point pose in robot base frame: x, y, z (m), rx, ry, rz (axis-angle, rad).",
        elements=[
            make_property("X_m",  0.0, model.datatypes.Double),
            make_property("Y_m",  0.0, model.datatypes.Double),
            make_property("Z_m",  0.0, model.datatypes.Double),
            make_property("Rx",   0.0, model.datatypes.Double),
            make_property("Ry",   0.0, model.datatypes.Double),
            make_property("Rz",   0.0, model.datatypes.Double),
        ],
    )
    submodel.submodel_element.add(tcp_pose)

    # Scalar status fields
    submodel.submodel_element.add(make_property(
        "RuntimeState", 0, model.datatypes.Int,
        description="0=stopped, 1=playing, 2=paused (UR controller convention).",
    ))
    submodel.submodel_element.add(make_property(
        "LastUpdated_unix_s", 0.0, model.datatypes.Double,
        description="Host wall-clock time of the last RTDE sample (seconds since epoch).",
    ))

    return submodel
