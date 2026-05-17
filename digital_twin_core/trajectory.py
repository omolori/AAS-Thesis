"""Canonical UR3 task definition used for all three pipeline comparisons.

Maps to thesis §3.x (experiment design): a pick-and-place cycle is the
canonical motion used to compare real UR3, URSim-default, and URSim-AAS
pipelines. Defining the trajectory as Python data (not a .urp file) keeps
it version-controlled and readable by every component.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Waypoint:
    name: str
    joint_positions_rad: tuple[float, float, float, float, float, float]
    dwell_s: float = 0.0


@dataclass(frozen=True)
class Trajectory:
    name: str
    waypoints: tuple[Waypoint, ...]
    speed_rad_s: float
    accel_rad_s2: float
    n_cycles: int


def pick_and_place_trajectory(
    speed_rad_s: float = 0.2,
    accel_rad_s2: float = 0.15,
    dwell_s: float = 0.5,
    n_cycles: int = 3,
) -> Trajectory:
    """8-waypoint pick-and-place task recorded from the physical UR3 with gripper.

    Passes back through the approach (pre_pick / pre_place) waypoints on the
    way up so the gripper never drags across the table surface.

    Waypoints jogged manually on the pendant, converted from degrees.
    TCP Z=0.241 m calibrated via 4-point method in PolyScope.
    """
    _HOME      = (-1.4561, -1.6660, -0.2774, -2.0748,  1.6275, -0.1098)
    _PRE_PICK  = (-1.3320, -1.8503, -1.7179, -1.1217,  1.5566,  0.2009)
    _PICK      = (-1.3428, -2.1051, -1.9055, -0.6799,  1.5585,  0.1948)
    _PRE_PLACE = (-1.1077, -1.9063, -1.7017, -1.0908,  1.6046,  0.4865)
    _PLACE     = (-1.1074, -2.1273, -1.8539, -0.7185,  1.6065,  0.4822)

    return Trajectory(
        name="pick_and_place",
        waypoints=(
            Waypoint("home",      _HOME),
            Waypoint("pre_pick",  _PRE_PICK),
            Waypoint("pick",      _PICK,      dwell_s=dwell_s),
            Waypoint("pre_pick",  _PRE_PICK),
            Waypoint("pre_place", _PRE_PLACE),
            Waypoint("place",     _PLACE,     dwell_s=dwell_s),
            Waypoint("pre_place", _PRE_PLACE),
            Waypoint("home",      _HOME),
        ),
        speed_rad_s=speed_rad_s,
        accel_rad_s2=accel_rad_s2,
        n_cycles=n_cycles,
    )
